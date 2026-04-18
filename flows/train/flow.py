"""
Train a model and register it as an asset.

This flow demonstrates the typical pattern:
  1. Load/generate training data
  2. Train a model
  3. Register both the data and model as assets on the current branch

When deployed from a feature branch, assets are written to that branch's namespace.
When deployed from main, assets go to the production namespace.

The key question this example addresses:
  What happens to these assets when the feature branch is merged and deleted?
  See the GitHub Actions workflow and promote_assets.py for the answer.
"""

from metaflow import step, Parameter
from obproject import ProjectFlow


class TrainClassifierFlow(ProjectFlow):
    """Train a fraud classifier and register it as a project asset."""

    n_samples = Parameter("n-samples", default=1000, type=int,
                          help="Number of training samples to generate")

    @step
    def start(self):
        """Generate synthetic training data."""
        from sklearn.datasets import make_classification
        import numpy as np

        X, y = make_classification(
            n_samples=self.n_samples,
            n_features=20,
            n_informative=10,
            random_state=42,
        )
        self.X_train = X
        self.y_train = y
        self.feature_names = [f"feature_{i}" for i in range(20)]

        # Register the training data as an asset
        self.prj.register_data("training_data", "X_train",
            annotations={
                "n_samples": str(len(X)),
                "n_features": str(X.shape[1]),
                "positive_rate": f"{np.mean(y):.3f}",
            },
            tags={"stage": "training"})

        self.next(self.train)

    @step
    def train(self):
        """Train the classifier."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score

        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        scores = cross_val_score(self.model, self.X_train, self.y_train, cv=5)
        self.model.fit(self.X_train, self.y_train)

        self.cv_accuracy = float(scores.mean())
        self.cv_std = float(scores.std())

        # Register the trained model as an asset
        self.prj.register_model("classifier", "model",
            annotations={
                "cv_accuracy": f"{self.cv_accuracy:.4f}",
                "cv_std": f"{self.cv_std:.4f}",
                "n_estimators": "100",
                "training_samples": str(len(self.X_train)),
            },
            tags={"status": "candidate"})

        print(f"Model trained: accuracy={self.cv_accuracy:.4f} +/- {self.cv_std:.4f}")
        self.next(self.end)

    @step
    def end(self):
        print(f"Registered model asset 'classifier' on branch '{self.prj.write_branch}'")
        print(f"Registered data asset 'training_data' on branch '{self.prj.write_branch}'")


if __name__ == "__main__":
    TrainClassifierFlow()
