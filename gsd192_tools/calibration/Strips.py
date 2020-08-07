from .Strip import Strip
from .file_utils import loadMCA

import numpy as np
from typing import List, Tuple, Any
from collections.abc import Sequence
import matplotlib.pyplot as plt

class Strips(Sequence):
    """
    Provides convenient functions for bulk operations on underlying Strip instances
    """
    def __init__(self, data:np.ndarray = None, path:str = None):
        """
        Parameters:
            data (np.ndarray): A 2D array of energy spectrums for every strip (.mca format)
            path (string): Alternatively the location of the .mca file
        """
        self.data = data
        if data is None and path:
            self.data = loadMCA(path)

        if self.data is None:
            raise ValueError("Need data or path")

        self.strips = [Strip(self.data[i], i) for i in range(self.data.shape[0])]

    def set_energies(self, energies:List[Tuple[int, float]], strip_index:int):
        """
        Set energies for all strips based on known energies for one strip. This will take a while.

        Parameters:
            energies (List[Tuple[int, float]]): The known energies for strip_index
            strip_index (int): The index of the strip the known energies are for
        """
        self.strips[strip_index].set_energies(energies)
        for strip in self.strips:
            if not strip.number == strip_index:
                strip.energies_from(self.strips[strip_index])

    def refine_energies(self, frame_width:int=20):
        """
        Refine energy locations using curve fitting
        """
        for strip in self.strips:
            strip.refine_energies(frame_width)

    def fit_polynomial(self, max_degree:int = 7, uniform_degree:bool = True) -> List[List[float]]:
        """
        Fit the highest degree polynomial possible with the available energy data. (0 degree is actually 1st degree with 0 shift)
        
        Parameters:
            max_degree (int): The highest order degree to try and fit (max: 7)
            uniform_degree (bool): In case on strip has more energies as another, still fit the same degree polynomial

        Returns:
            (List[List[Float]]): 2D Array of coefficients (highest to lowest order) for every strip
        """
        if uniform_degree:
            min_degree = max_degree
            for strip in self.strips:
                min_degree = min(min_degree, len(strip.energies)-1)
            max_degree = min_degree

        out = []
        for strip in self.strips:
            out.append(strip.fit_polynomial(max_degree=max_degree))
        return out

    def calibrated_x(self) -> np.ndarray:
        """
        Get an array containing a calibrated x value for every point in the original data

        Returns:
            (np.ndarray): 2D array containing x values for every strip
        """
        return np.asarray([strip.calibrated_x() for strip in self.strips])

    def interpolate(self, xmin:float = None, xmax:float = None, step_size:float = 0.1, exclude_strips:List[int] = []) -> Tuple[np.ndarray, float, float]:
        """
        Interpolate the data to the calibrated x values

        Parameters:
            xmin (float): The minimum energy for a point to be included
            xmax (float): The maximum energy for a point to be included
            step_size (float): The difference in energy between indices (Ex: 0.1 will cause indices to be 10x the actual energy value)
            exclude_strips (List[int]): Indices of strips to exclude (set to all zeros). This can be useful if there are faulty strips.

        Returns:
            (List[np.ndarray, float, float]): The interpolated data, xmin, xmax
        """
        xs = np.asarray([strip.calibrated_x() for strip in self.strips])

        include_mask = [i not in exclude_strips for i in range(0, len(self.strips))]
        if xmin is None:
            xmin = xs[:, 0].max(where=include_mask, initial=-np.Infinity)
        if xmax is None:
            xmax = xs[:, -1].min(where=include_mask, initial=np.Infinity)

        x_range = np.arange(xmin, xmax, step=step_size)
        return np.asarray([np.interp(x_range, xs[i], self.strips[i].data) if i not in exclude_strips else np.zeros(x_range.shape) for i in range(len(self.strips))]), xmin, xmax

    def imshow(self, calibrated:bool = True, calibrated_units:str = "keV", log_scale:bool = True, exclude_strips:List[int] = [], *args, **kwargs):
        """
        Plot the data with matplotlib's imshow function. All extra arguments will be passed to imshow

        Parameters:
            calibrated (bool): Use the calibrated x values if possible
            calibrated_units (string): The units of the energy values used for calibration
            log_scale (bool): Log data before plotting
        """
        if calibrated:
            for strip in self.strips:
                if not strip.energies and not strip.refined_energies:
                    break
            else:
                plt.ylabel("Strip number")
                plt.xlabel("Energy ({})".format(calibrated_units))
                data, xmin, xmax = self.interpolate(exclude_strips=exclude_strips)
                plt.imshow(np.log10(data), extent=(xmin, xmax, len(self.strips), 0), aspect='auto', cmap='winter', interpolation='nearest', *args, **kwargs)
                plt.show()
                return

        plt.ylabel("Strip number")
        plt.xlabel("Detector Energy Channel")
        plt.imshow(np.log10(self.data), extent=(0, self.data.shape[1], len(self.strips), 0), aspect='auto', cmap='winter', interpolation='nearest', *args, **kwargs)
        plt.show()

    def __getitem__(self, index):
        return self.strips[index]

    def __len__(self):
        return len(self.strips)