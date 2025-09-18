import torch
import torch.nn as nn
from typing import Iterable, Optional, List


class QuantizedIoUMetric:
    """
    Computes a Quantized Intersection over Union (IoU) metric for regression tasks
    where the output and target are 2D matrices with values between 0 and 1.

    The primary method involves quantizing continuous values into a set of discrete
    intervals (bins) and then calculating the IoU for each interval. The final
    metric is the average of these individual interval IoUs.

    Note: Cells in the target tensor with a value of -1 are ignored in all calculations.

    - `__call__`: Computes the mean quantized IoU over all intervals.
    - `mean_quantized_iou_le`, `mean_quantized_iou_gt`, `mean_quantized_iou_between`:
      Compute the mean quantized IoU for a subset of intervals derived from a value threshold.

    Attributes:
        num_intervals (int): The number of quantization levels (intervals).
        epsilon (float): A small value to avoid division by zero.
        bins (Optional[List[float]]): A list of boundary values for custom intervals.
    """

    def __init__(self, num_intervals: Optional[int] = None, bins: Optional[List[float]] = None, epsilon: float = 1e-6):
        """
        Initializes the QuantizedIoUMetric instance.

        Args:
            num_intervals (Optional[int]): The number of discrete intervals to use for
                                 quantization. This is ignored if `bins` are provided.
                                 Defaults to 10.
            bins (Optional[List[float]]): A list of boundary values for custom intervals.
                                          e.g., [0.0, 0.2, 0.5, 1.0] creates 3 bins.
                                          The list must be sorted, start with 0.0,
                                          end with 1.0, and contain unique values.
                                          Defaults to None.
            epsilon (float): A small constant to add to the denominator to
                             prevent division by zero. Defaults to 1e-6.
        """
        if bins is not None:
            if not isinstance(bins, list) or len(bins) < 2 or bins[0] != 0.0 or bins[-1] != 1.0 or sorted(list(set(bins))) != bins:
                raise ValueError("If 'bins' is provided, it must be a sorted list of unique values starting with 0.0 and ending with 1.0.")
            self.bins = bins
            self.num_intervals = len(bins) - 1
        else:
            if not isinstance(num_intervals, int) or num_intervals <= 0:
                raise ValueError("num_intervals must be a positive integer if bins are not provided.")
            self.num_intervals = num_intervals
            self.bins = [i / self.num_intervals for i in range(self.num_intervals + 1)]

        self.epsilon = epsilon
        self._bin_tensor = torch.tensor(self.bins[:-1])

    def _value_to_interval_index(self, value: float) -> int:
        """Converts a float value [0, 1] to its corresponding interval index."""
        if not (0.0 <= value <= 1.0):
            raise ValueError("Value must be between 0.0 and 1.0.")

        # Find the first bin boundary that is strictly greater than the value
        # The index of this boundary is the bin index for the value.
        # Example: bins = [0.0, 0.2, 0.5, 1.0].
        # value=0.1 -> searchsorted finds index 1 (boundary 0.2), so bin index is 0.
        # value=0.2 -> searchsorted finds index 2 (boundary 0.5), so bin index is 1.
        # Clamp to handle values exactly equal to 1.0
        return max(0, torch.searchsorted(torch.tensor(self.bins, dtype=torch.float32), value, right=True).item() - 1)

    def _calculate_mean_iou_for_intervals(self, output_classes: torch.Tensor, target_classes: torch.Tensor,
                                          intervals: Iterable[int]) -> torch.Tensor:
        """Private helper to calculate mean IoU over a specified set of intervals."""
        iou_scores = []
        device = output_classes.device

        for i in intervals:
            output_mask = (output_classes == i)
            target_mask = (target_classes == i)
            intersection = torch.logical_and(output_mask, target_mask).sum()
            union = torch.logical_or(output_mask, target_mask).sum()

            if union == 0:
                # If there are no target or output cells in this interval,
                # the IoU is considered 1.0, as there is no false positive or
                # false negative for this class.
                iou = torch.tensor(1.0, device=device)
            else:
                iou = intersection.float() / (union.float() + self.epsilon)
            iou_scores.append(iou)

        if not iou_scores:
            return torch.tensor(0.0, device=device)
        return torch.stack(iou_scores).mean()

    def __call__(self, output: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """
        Calculates the mean quantized IoU score across all intervals.
        """
        if output.shape != target.shape:
            raise ValueError("Output and target tensors must have the same shape.")

        valid_mask = (target != -1)
        if not valid_mask.any():
            return torch.tensor(0.0, device=output.device)

        output_valid = output[valid_mask]
        target_valid = target[valid_mask]

        if self.bins is not None:
            # For custom bins, we can use torch.bucketize
            output_classes = torch.bucketize(output_valid.float(), torch.tensor(self.bins, device=output_valid.device), right=True) - 1
            output_classes = torch.clamp(output_classes, min=0, max=self.num_intervals - 1)
            target_classes = torch.bucketize(target_valid.float(), torch.tensor(self.bins, device=target_valid.device), right=True) - 1
            target_classes = torch.clamp(target_classes, min=0, max=self.num_intervals - 1)
        else:
            # Original logic for uniform intervals
            output_classes = torch.clamp((output_valid * self.num_intervals).long(), max=self.num_intervals - 1)
            target_classes = torch.clamp((target_valid * self.num_intervals).long(), max=self.num_intervals - 1)

        all_intervals = range(self.num_intervals)
        return self._calculate_mean_iou_for_intervals(output_classes, target_classes, all_intervals)

    def mean_quantized_iou_le(self, output: torch.Tensor, target: torch.Tensor, max_value: float) -> torch.Tensor:
        """
        Calculates mean quantized IoU for intervals corresponding to values LESS THAN OR EQUAL TO a threshold.
        """
        if output.shape != target.shape:
            raise ValueError("Output and target tensors must have the same shape.")

        valid_mask = (target != -1)
        if not valid_mask.any():
            return torch.tensor(0.0, device=output.device)

        output_valid = output[valid_mask]
        target_valid = target[valid_mask]

        max_interval_index = self._value_to_interval_index(max_value)

        if self.bins is not None:
            output_classes = torch.bucketize(output_valid.float(), torch.tensor(self.bins, device=output_valid.device), right=True) - 1
            output_classes = torch.clamp(output_classes, min=0, max=self.num_intervals - 1)
            target_classes = torch.bucketize(target_valid.float(), torch.tensor(self.bins, device=target_valid.device), right=True) - 1
            target_classes = torch.clamp(target_classes, min=0, max=self.num_intervals - 1)
        else:
            output_classes = torch.clamp((output_valid * self.num_intervals).long(), max=self.num_intervals - 1)
            target_classes = torch.clamp((target_valid * self.num_intervals).long(), max=self.num_intervals - 1)

        selected_intervals = range(max_interval_index + 1)
        return self._calculate_mean_iou_for_intervals(output_classes, target_classes, selected_intervals)

    def mean_quantized_iou_between(self, output: torch.Tensor, target: torch.Tensor, min_value: float,
                                   max_value: float) -> torch.Tensor:
        """
        Calculates mean quantized IoU for intervals BETWEEN two value thresholds (inclusive).
        """
        if output.shape != target.shape:
            raise ValueError("Output and target tensors must have the same shape.")

        valid_mask = (target != -1)
        if not valid_mask.any():
            return torch.tensor(0.0, device=output.device)

        output_valid = output[valid_mask]
        target_valid = target[valid_mask]

        min_interval_index = self._value_to_interval_index(min_value)
        max_interval_index = self._value_to_interval_index(max_value)

        if min_interval_index > max_interval_index:
            return torch.tensor(0.0, device=output.device)

        if self.bins is not None:
            output_classes = torch.bucketize(output_valid.float(), torch.tensor(self.bins, device=output_valid.device), right=True) - 1
            output_classes = torch.clamp(output_classes, min=0, max=self.num_intervals - 1)
            target_classes = torch.bucketize(target_valid.float(), torch.tensor(self.bins, device=target_valid.device), right=True) - 1
            target_classes = torch.clamp(target_classes, min=0, max=self.num_intervals - 1)
        else:
            output_classes = torch.clamp((output_valid * self.num_intervals).long(), max=self.num_intervals - 1)
            target_classes = torch.clamp((target_valid * self.num_intervals).long(), max=self.num_intervals - 1)

        selected_intervals = range(min_interval_index, max_interval_index + 1)
        return self._calculate_mean_iou_for_intervals(output_classes, target_classes, selected_intervals)

    def mean_quantized_iou_gt(self, output: torch.Tensor, target: torch.Tensor, min_value: float) -> torch.Tensor:
        """
        Calculates mean quantized IoU for intervals corresponding to values GREATER THAN a threshold.
        """
        if output.shape != target.shape:
            raise ValueError("Output and target tensors must have the same shape.")

        valid_mask = (target != -1)
        if not valid_mask.any():
            return torch.tensor(0.0, device=output.device)

        output_valid = output[valid_mask]
        target_valid = target[valid_mask]

        min_interval_index = self._value_to_interval_index(min_value)

        if self.bins is not None:
            output_classes = torch.bucketize(output_valid.float(), torch.tensor(self.bins, device=output_valid.device), right=True) - 1
            output_classes = torch.clamp(output_classes, min=0, max=self.num_intervals - 1)
            target_classes = torch.bucketize(target_valid.float(), torch.tensor(self.bins, device=target_valid.device), right=True) - 1
            target_classes = torch.clamp(target_classes, min=0, max=self.num_intervals - 1)
        else:
            output_classes = torch.clamp((output_valid * self.num_intervals).long(), max=self.num_intervals - 1)
            target_classes = torch.clamp((target_valid * self.num_intervals).long(), max=self.num_intervals - 1)

        selected_intervals = range(min_interval_index + 1, self.num_intervals)
        return self._calculate_mean_iou_for_intervals(output_classes, target_classes, selected_intervals)


# --- Example Usage with Custom Bins ---
if __name__ == '__main__':
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Instantiate with custom bins: two narrow bins at the start, two wide bins at the end
    custom_bins = [0.0, 0.1, 0.2, 0.6, 1.0]
    custom_iou_metric = QuantizedIoUMetric(bins=custom_bins)
    print(f"\nInitialized metric with custom bins: {custom_bins}")
    print(f"Number of intervals: {custom_iou_metric.num_intervals}")

    # Tensors for testing
    output_tensor_custom = torch.rand(100, 100, device=device)
    target_tensor_custom = torch.rand(100, 100, device=device)

    # --- Test Case 1: Mean Quantized IoU (all intervals) ---
    print("\n--- Test Case 1: Mean Quantized IoU (all intervals) ---")
    quantized_iou_custom = custom_iou_metric(output_tensor_custom, target_tensor_custom)
    print(f"Mean Quantized IoU (all intervals, custom bins): {quantized_iou_custom.item():.4f}")

    # --- Test Case 2: Mean Quantized IoU for values <= 0.2 ---
    print("\n--- Test Case 2: Mean Quantized IoU for values <= 0.2 ---")
    le_iou_custom = custom_iou_metric.mean_quantized_iou_le(output_tensor_custom, target_tensor_custom, max_value=0.2)
    print(f"Mean Quantized IoU for intervals <= 0.2: {le_iou_custom.item():.4f}")

    # --- Test Case 3: Mean Quantized IoU for values > 0.2 ---
    print("\n--- Test Case 3: Mean Quantized IoU for values > 0.2 ---")
    gt_iou_custom = custom_iou_metric.mean_quantized_iou_gt(output_tensor_custom, target_tensor_custom, min_value=0.2)
    print(f"Mean Quantized IoU for intervals > 0.2: {gt_iou_custom.item():.4f}")

    # --- Test Case 4: Mean Quantized IoU for values between [0.1, 0.6] ---
    print("\n--- Test Case 4: Mean Quantized IoU for values between [0.1, 0.6] ---")
    between_iou_custom = custom_iou_metric.mean_quantized_iou_between(output_tensor_custom, target_tensor_custom, min_value=0.1, max_value=0.6)
    print(f"Mean Quantized IoU for intervals between [0.1, 0.6]: {between_iou_custom.item():.4f}")