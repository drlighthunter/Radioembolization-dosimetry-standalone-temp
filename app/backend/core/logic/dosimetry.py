import numpy as np
import SimpleITK as sitk
import logging

class DosimetryEngine:
    """
    Pure Python implementation of the Radioembolization Dosimetry logic
    originally developed for 3D Slicer.
    """
    def __init__(self, conversion_factor=49.67, liver_density=1.05, lung_mass=1000.0):
        self.conversion_factor = conversion_factor  # Gy/MBq/g (Default for Y-90: 49.67 J/GBq)
        self.liver_density = liver_density          # g/mL
        self.lung_mass = lung_mass                  # g

    def calculate_dose(self, 
                       spect_volume: sitk.Image, 
                       segmentation_mask: sitk.Image, 
                       liver_label_value: int, 
                       activity_mbq: float, 
                       lung_shunt_fraction_percent: float):
        """
        Ported from Slicer's calculateDose function.
        """
        logging.info("Starting dosimetric calculations.")

        # 1. Mask the SPECT volume with the liver segment
        # Ensure segmentation and spect are in same space (SimpleITK handles this better than raw numpy)
        mask_filter = sitk.MaskImageFilter()
        mask_filter.SetOutsideValue(0)
        masked_spect = mask_filter.Execute(spect_volume, sitk.Cast(segmentation_mask == liver_label_value, sitk.sitkUInt8))

        # 2. Convert to numpy for calculations
        masked_array = sitk.GetArrayFromImage(masked_spect)
        
        # 3. Calculate total volume in mL
        spacing = spect_volume.GetSpacing()
        voxel_volume_ml = (spacing[0] * spacing[1] * spacing[2]) / 1000.0
        
        # Calculate voxel count in the mask
        liver_voxel_mask = (sitk.GetArrayFromImage(segmentation_mask) == liver_label_value)
        liver_voxel_count = np.sum(liver_voxel_mask)
        total_volume_ml = liver_voxel_count * voxel_volume_ml

        if total_volume_ml == 0:
            raise ValueError("Total liver volume is zero. Check segmentation.")

        # 4. Adjust activity based on lung shunt fraction
        lung_shunt_fraction = lung_shunt_fraction_percent / 100.0
        net_activity_mbq = activity_mbq * (1 - lung_shunt_fraction)

        # 5. Calculate mean input value within the liver segment
        # In Slicer: meanInputValue = np.sum(maskedArray) / maskedArray.size
        # Note: Slicer's maskedArray.size includes outside voxels if not careful.
        # We should use the sum of intensities divided by the number of liver voxels.
        sum_intensity = np.sum(masked_array)
        mean_input_value = sum_intensity / liver_voxel_count

        # 6. Calculate mean output dose (Gy)
        # Formula: (Activity / (Volume * Density)) * Conversion
        mean_output_dose_gy = (net_activity_mbq / (total_volume_ml * self.liver_density)) * self.conversion_factor

        # 7. Rescale factor to normalize dose
        if mean_input_value == 0:
             rescale_factor = 0
        else:
             rescale_factor = mean_output_dose_gy / mean_input_value

        # 8. Create Dose Map
        dose_array = masked_array * rescale_factor
        dose_image = sitk.GetImageFromArray(dose_array)
        dose_image.CopyInformation(spect_volume)

        # 9. Calculate Segment Doses
        # We need a way to pass other segment labels here... 
        # For now, let's return the basic stats.
        
        # Estimate lung absorbed dose
        lung_dose_gy = (activity_mbq * lung_shunt_fraction * self.conversion_factor) / self.lung_mass

        return {
            "dose_image": dose_image,
            "mean_liver_dose_gy": mean_output_dose_gy,
            "lung_dose_gy": lung_dose_gy,
            "liver_volume_ml": total_volume_ml,
            "rescale_factor": rescale_factor
        }
