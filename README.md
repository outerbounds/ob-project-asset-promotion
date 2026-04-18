# Versioning Assets Across Branches

This example project demonstrates how Outerbounds Projects handles model and
data assets across git branches — the branch-scoped lifecycle, what to be aware
of during branch transitions, and the patterns for promoting assets between
branches.

## How branch-scoped assets work

Assets are **metadata pointers scoped to a project branch**. When you register
a model on branch `feature-v2`, the catalog entry lives at
`project/feature-v2/models/classifier`. The actual model weights live in S3 (or
Metaflow's datastore) and are **not** scoped to a branch.

This gives you isolation: each branch has its own asset namespace for
experimentation, without risk of overwriting production data.

### What the backend actually stores

Each asset registration creates two S3 objects:

1. An **instance** at a timestamped path (the versioned record)
2. A **`latest` pointer** that gets overwritten on each registration

When you request `instance="latest"`, the backend does a direct S3 key read —
no timestamp sorting, no query. Aliases (`@champion`, `@staging`) are stored
separately and resolved when the instance ID starts with `@`.

### The branch lifecycle gap

When a branch is deleted (after PR merge, or manually), `teardown-branch`
removes the branch-scoped asset metadata. The underlying S3 objects survive, but
the catalog entries — the pointers saying "this model exists, here's where to
find it" — are gone.

If you trained a model on a feature branch and want those weights available on
`main`, you need to explicitly move the metadata before (or instead of)
teardown.

## Promotion strategies

| Strategy | When to use | Cost |
|---|---|---|
| **Re-run on main** | Training is cheap, reproducibility matters most | Compute time |
| **Cross-branch promotion** | Training is expensive, same weights should serve prod | ~Free (metadata only) |
| **Alias-based** | Staging gates within a single branch | ~Free |

### Re-run on main

Merge your code, let the scheduled or triggered training flow run on `main`. It
produces the canonical production asset. No special CI/CD needed.

Use when training takes minutes, or you want the guarantee that the production
model was built from exactly the main branch code.

### Cross-branch promotion

Read the source branch's asset instances and re-register them on the target
branch with the same blob references. The model weights don't move — only the
metadata pointer is created.

```python
from obproject.assets import promote_assets

# Promote everything from feature branch to main
result = promote_assets('my_project', source='feature-v2', target='main')

# Promote only models
result = promote_assets('my_project', source='feature-v2', target='main',
                        kinds=['models'])

# Promote a specific validated model instance
result = promote_assets('my_project', source='feature-v2', target='main',
                        asset='classifier', instance='@validated')
```

```
┌─────────────┐   promote_assets()   ┌─────────────┐
│ feature-v2  │ ────────────────────> │    main      │
│ models/     │   (re-register       │ models/     │
│  classifier │    same blobs ref)   │  classifier │
└─────────────┘                      └─────────────┘
     S3: s3://bucket/model.pkl ─── same object, not copied ──>
```

Promoted instances include lineage annotations (`promoted_from_branch`,
`promoted_from_instance`) so you can trace where the production asset
originated.

Use when training is expensive (GPU-hours, large fine-tunes) and the feature
branch model has been validated.

### Alias-based promotion

Use aliases like `@champion`, `@staging`, `@production` to tag specific
instances **within a branch**. This is orthogonal to cross-branch promotion —
you can combine both:

```python
# Promote the @validated instance across branches
promote_assets('my_project', source='feature-v2', target='main',
               asset='classifier', instance='@validated')
```

## CI/CD integration

The `.github/workflows/deploy.yml` in this project shows the pattern:

1. **Deploy** on push/PR (standard `obproject-deploy`)
2. **Promote** on PR merge — call `promote_assets()` before teardown
3. **Teardown** the feature branch

The promote step is:

```yaml
- name: Promote assets to main
  run: |
    python3 -c "
    from obproject.assets import promote_assets
    result = promote_assets('$PROJECT', source='$BRANCH', target='main')
    for p in result['promoted']:
        print(f'Promoted {p[\"kind\"]}/{p[\"name\"]}')
    "
```

## Branch semantics recap

| Context | Write Branch | Read Branch | Notes |
|---|---|---|---|
| Deployed from `main` | `main` | `main` | Production. Self-contained. |
| Deployed from `feature-v2` | `feature-v2` | `feature-v2` | Isolated testing. |
| Feature + `[dev-assets]` | `feature-v2` | `main` | Test new code against prod data. |
| Local run + `[dev-assets]` | `user.<name>` | `main` | Dev against prod assets. |

## Project structure

```
ob-project-asset-promotion/
├── obproject.toml                    # Project config with [dev-assets]
├── .github/workflows/deploy.yml     # Deploy + promote + teardown
├── flows/
│   ├── train/flow.py                # Trains model, registers assets
│   └── inference/flow.py            # Consumes model from read branch
├── models/classifier/
│   └── asset_config.toml            # Model asset definition
└── data/training_data/
    └── asset_config.toml            # Data asset definition
```
