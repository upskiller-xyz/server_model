import torch

class ThresholdAccuracy:
    """
    A functor to calculate the threshold accuracy for depth estimation.
    """
    def __init__(self, threshold):
        """
        Initializes the functor with a threshold.
        Args:
            threshold (float): The threshold value. Common values are 1.25, 1.25^2, etc.
        """
        self.threshold = threshold

    def __call__(self, prediction, target):
        """
        Calculates the threshold accuracy.
        Args:
            prediction (torch.Tensor): The predicted depth map.
            target (torch.Tensor): The ground truth depth map.
        Returns:
            float: The threshold accuracy as a percentage.
        """
        # Ensure tensors are on the same device and have the same shape
        if prediction.shape != target.shape:
            raise ValueError("Prediction and target tensors must have the same shape.")

        # Ignore pixels where target depth is 0 (occlusions or invalid data)
        valid_pixels = target > 0

        # Calculate the ratio
        ratio = torch.max(prediction[valid_pixels] / target[valid_pixels], target[valid_pixels] / prediction[valid_pixels])

        # Count the number of pixels where the ratio is less than the threshold
        correct_pixels = torch.sum(ratio < self.threshold)
        total_pixels = torch.sum(valid_pixels)

        # Calculate accuracy as a percentage
        accuracy = (correct_pixels.float() / total_pixels.float()) * 100

        return accuracy.item()