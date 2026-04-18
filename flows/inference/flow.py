"""
Consume the classifier model asset for inference.

This flow reads the model from the read_branch (typically main in production).
It demonstrates the consumer side of the asset lifecycle.
"""

from metaflow import step
from obproject import ProjectFlow


class InferenceFlow(ProjectFlow):
    """Load the production model and run inference."""

    @step
    def start(self):
        """Load the model asset from the read branch."""
        self.model = self.prj.get_model("classifier")
        print(f"Loaded classifier from branch '{self.prj.branch}'")
        self.next(self.predict)

    @step
    def predict(self):
        """Run inference on synthetic data."""
        from sklearn.datasets import make_classification
        import numpy as np

        X_test, y_test = make_classification(
            n_samples=200,
            n_features=20,
            n_informative=10,
            random_state=99,
        )

        predictions = self.model.predict(X_test)
        accuracy = float(np.mean(predictions == y_test))
        print(f"Test accuracy: {accuracy:.4f}")

        self.predictions = predictions
        self.test_accuracy = accuracy
        self.next(self.end)

    @step
    def end(self):
        print(f"Inference complete. Accuracy: {self.test_accuracy:.4f}")


if __name__ == "__main__":
    InferenceFlow()
