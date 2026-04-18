# Versioning Assets Across Branches

Assets in Outerbounds Projects are metadata pointers scoped to git branches.
The actual data (model weights, datasets) lives in S3. When a feature branch
is deleted, for example to clean up workflows and app deployments after a feature branch is merged, `outerbounds flowproject teardown-branch` can be used to remove the asset metadata as well. The S3
objects survive in the same way Metaflow artifacts do if you delete workflows deployments after having already run them, but the catalog entries pointing to them are gone.

`promote_assets()` solves this: it copies asset metadata from one branch to
another before teardown, so the same underlying weights/data become available
on the target branch without re-training or copying bytes.

## Usage

```python
from obproject.assets import promote_assets

# Promote all assets
promote_assets('my_project', source='feature-v2', target='main')

# Promote only models, with aliases carried forward
promote_assets('my_project', source='feature-v2', target='main',
               kinds=['models'], with_aliases=True)

# Promote a specific aliased instance
promote_assets('my_project', source='feature-v2', target='main',
               asset='classifier', instance='@validated')
```

Promoted instances get `promoted_from_branch` and `promoted_from_instance`
annotations for lineage.

## CI/CD

The included GitHub Actions workflow (`.github/workflows/deploy.yml`) runs
three steps on PR merge:

1. **Deploy** code to the target branch (`obproject-deploy`)
2. **Promote** assets from the source branch to the target branch
3. **Teardown** the source branch

Ordering matters — promote must run before teardown. The workflow handles this.

## When to promote vs. re-run

**Promote** when training is expensive and the feature branch model has been
validated. **Re-run** when training is cheap and you want the guarantee that
production artifacts were built from the merged code. Most projects use a mix.

## Project structure

```
ob-project-asset-promotion/
├── obproject.toml                    # [dev-assets] reads from main
├── .github/workflows/deploy.yml     # deploy + promote + teardown
├── flows/
│   ├── train/flow.py                # trains model, registers assets
│   └── inference/flow.py            # consumes model from read branch
├── models/classifier/asset_config.toml
└── data/training_data/asset_config.toml
```
