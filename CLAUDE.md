# Cross-Branch Asset Promotion

When you train a model on a feature branch, the model asset lives in that branch's namespace. When the branch is merged and deleted, the asset would be lost. This project demonstrates the CI-driven promotion pattern: on PR merge, `promote_assets()` copies assets from the feature branch to main before teardown deletes the branch.

This is the reference implementation of the promote + teardown CI workflow.

## Architecture

```
TrainClassifierFlow (manual, on feature branch)
  → trains model, registers "classifier" ModelAsset + "training_data" DataAsset
  → assets scoped to feature branch namespace

InferenceFlow (manual, reads from production)
  → loads "classifier" from read branch (main via [dev-assets])
  → runs inference

CI on PR merge:
  → promote_assets(source=feature_branch, target=main, with_aliases=True)
  → teardown-branch (deletes feature branch resources)
  → model now lives on main, survives branch deletion
```

## Platform features used

- **Asset branch scoping**: Assets written to current branch namespace, read from [dev-assets] branch
- **promote_assets()**: CI-driven asset copy from feature branch to main on merge
- **teardown-branch**: Clean up Argo resources after promotion
- **[dev-assets]**: InferenceFlow reads production model from main during development
- **@pypi**: Per-step dependency management

## Flows

| Flow | Trigger | What it does |
|------|---------|-------------|
| TrainClassifierFlow | Manual | Train model, register data + model assets |
| InferenceFlow | Manual | Load production model, run inference |

## CI strategy

Deploy + promote + teardown. The most complete lifecycle:
1. **Push**: deploys to main, feature/*, test/* branches
2. **PR merge**: promotes assets from feature branch to main, then tears down
3. **Branch delete (no PR)**: teardown only, no promotion

The promote step calls `promote_assets(with_aliases=True)` which copies alias assignments along with asset instances.

Uses `--from-obproject-toml` for auth. Promote and teardown extract project name via `python3 tomllib` (since those commands don't support `--from-obproject-toml` yet).

## Run locally

```bash
python flows/train/flow.py run
python flows/inference/flow.py run
```

## Good to know

- Promotion is a CI concern, not a flow concern. Flows don't need to know about branch lifecycle.
- `promote_assets(with_aliases=True)` copies aliases (e.g., "champion") along with assets. Without it, only the asset instance is copied.
- InferenceFlow uses `prj.get_model("classifier")` which reads from the [dev-assets] branch (main). On a feature branch, this loads the production model — not the one you just trained. This is intentional: consumer flows should read from production.
- The promote-and-teardown job has `needs: deploy` and `always()` — it runs even if deploy fails, to clean up.
