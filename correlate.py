#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  6 10:39:28 2024

@author: paul
"""

import numpy as  np
import numba
import tables as tb

from vispy import scene, app

import config

@numba.jit(numba.float64[:](numba.float64[:], numba.int64[:], numba.int64[:], numba.int64[:]), nopython=True)
def pnormalize(G, t, u, bins):
    r"""Normalize point-process cross-correlation function.

    This normalization is usually employed for fluorescence correlation
    spectroscopy (FCS) analysis.
    The normalization is performed according to
    `(Laurence 2006) <https://doi.org/10.1364/OL.31.000829>`__.
    Basically, the input argument `G` is multiplied by:

    .. math::
        \frac{T-\tau}{n(\{i \ni t_i \le T - \tau\})n(\{j \ni u_j \ge \tau\})}

    where `n({})` is the operator counting the elements in a set, *t* and *u*
    are the input arrays of the correlation, *τ* is the time lag and *T*
    is the measurement duration.

    Arguments:
        G (array): raw cross-correlation to be normalized.
        t (array): first input array of "points" used to compute `G`.
        u (array): second input array of "points" used to compute `G`.
        bins (array): array of bins used to compute `G`. Needs to have the
            same units as input arguments `t` and `u`.

    Returns:
        Array of normalized values for the cross-correlation function,
        same size as the input argument `G`.
    """
    duration = max((t.max(), u.max())) - min((t.min(), u.min()))
    Gn = G.copy()
    for i, tau in enumerate(bins[1:]):
        Gn[i] *= ((duration - tau) /
                  (float((t >= tau).sum()) *
                   float((u <= (u.max() - tau)).sum())))
    return Gn




@numba.jit(numba.float64[:](numba.int64[:], numba.int64[:], numba.int64[:]), nopython=True)
def pcorrelate(t, u, bins):
    """Compute correlation of two arrays of discrete events (Point-process).

    The input arrays need to be values of a point process, such as
    photon arrival times or positions. The correlation is efficiently
    computed on an arbitrary array of lag-bins. As an example, bins can be
    uniformly spaced in log-space and span several orders of magnitudes.
    (you can use :func:`make_loglags` to creat log-spaced bins).
    This function implements the algorithm described in
    `(Laurence 2006) <https://doi.org/10.1364/OL.31.000829>`__.

    Arguments:
        t (array): first array of "points" to correlate. The array needs
            to be monothonically increasing.
        u (array): second array of "points" to correlate. The array needs
            to be monothonically increasing.
        bins (array): bin edges for lags where correlation is computed.
        normalize (bool): if True, normalize the correlation function
            as typically done in FCS using :func:`pnormalize`. If False,
            return the unnormalized correlation function.

    Returns:
        Array containing the correlation of `t` and `u`.
        The size is `len(bins) - 1`.

    See also:
        :func:`make_loglags` to genetate log-spaced lag bins.
    """
    nbins = len(bins) - 1

    # Array of counts (histogram)
    counts = np.zeros(nbins, dtype=np.int64)

    # For each bins, imin is the index of first `u` >= of each left bin edge
    imin = np.zeros(nbins, dtype=np.int64)
    # For each bins, imax is the index of first `u` >= of each right bin edge
    imax = np.zeros(nbins, dtype=np.int64)

    # For each ti, perform binning of (u - ti) and accumulate counts in Y
    for ti in t:
        for k, (tau_min, tau_max) in enumerate(zip(bins[:-1], bins[1:])):
            #print ('\nbin %d' % k)

            if k == 0:
                j = imin[k]
                # We start by finding the index of the first `u` element
                # which is >= of the first bin edge `tau_min`
                while j < len(u):
                    if u[j] - ti >= tau_min:
                        break
                    j += 1

            imin[k] = j
            if imax[k] > j:
                j = imax[k]
            while j < len(u):
                if u[j] - ti >= tau_max:
                    break
                j += 1
            imax[k] = j
            # Now j is the index of the first `u` element >= of
            # the next bin left edge
        counts += imax - imin
    G = counts / (bins[1:]-bins[:-1])
    G = pnormalize(G, t, u, bins)
    return G

# ensure pcorrelate is compiled on import
_t = np.array([2,4,6,29], dtype=np.int64)
_bins = np.array([1, 2, 3, 4], dtype=np.int64)
_out = pcorrelate(_t, _t, _bins)
del _t, _bins, _out

def load_hdf5(filename):
    """
    Read a photon hdf5 file

    Parameters
    ----------
    filename : str
        Name of file to open.

    Returns
    -------
    time : np.ndarray
        Arrival times of photons.
    det : np.ndarray
        Detectors of photons.
    clk : float
        Clock rate in seconds (i.e. a value of 1 in times = clk seconds)
        Divide time by clk to get time of photon in seconds.

    """
    with tb.open_file(filename, 'r') as f:
        clk = f.root.photon_data.timestamps_specs.timestamps_unit.read()
        det = f.root.photon_data.detectors.read()
        time = f.root.photon_data.timestamps.read()
    return time, det, clk


@numba.jit(nopython=True)
def proc_csv(data, expand):
    photons = data[:, 1:].sum()
    times, dets = np.empty((photons, ), dtype=np.int64), np.empty((photons, ), dtype=np.int64)
    i = 0
    if expand:
        expand_by = data[:, 1:].max()
        data[:,0] = expand_by*data[:,0]
        for t, b, g in data:
            for j in range(b):
                times[i] = t + j
                dets[i] = 0
                i += 1
            for j in range(g):
                times[i] = t + j + b
                dets[i] = 1
                i += 1
    else:
        expand_by = 1
        for t, b, g in data:
            for _ in range(b):
                times[i] = t
                dets[i] = 0
                i += 1
            for _ in range(g):
                times[i] = t
                dets[i] = 1
                i += 1
    return times, dets, expand_by


def load_csv(filename, expand=False):
    """
    Load a csv file and convert to photon-list.

    Parameters
    ----------
    filename : str
        Name of csv file to open.
    expand : bool, optional
        Whether or not to make all arrival times unique by "expanding" arrival
        time by maximum number of photons seen at a given time. The default is False.

    Returns
    -------
    times : np.ndarray[np.int64]
        Arrival times of photons.
    dets : np.ndarray[np.int32]
        Detector indexes (0 or 1) of each photon.
    expand_by : int
        Factor by which times have been multiplied.

    """
    data = np.genfromtxt(filename, skip_header=1, delimiter=',', dtype=np.int64)
    times, dets, expand_by = proc_csv(data, expand)
    return times, dets, expand_by


def _get_mask(dets, det):
    """
    Internal function returns mask of all dets that match det.
    Det can be an integer, or array of integers.
    Purpose is to make this input flextible.
    Mimics dets == det

    Parameters
    ----------
    dets : np.ndarray[int]
        Array of detector indexes.
    det : int | tuple | np.ndarray)
        Detectors of interest.

    Returns
    -------
    mask : np.ndarray[bool]
        Boolean mask of which dets match det.

    """
    if np.issubdtype(type(det), np.integer):
        mask = dets == det
    else:
        mask = np.zeros(dets.size, dtype=bool)
        for d in det:
            mask += dets == d
    return mask


def process_buffers(buf, transfer_idx, ndet, dets, corr_all):
    buf_arr = np.array(buf[:transfer_idx], dtype=np.int64)
    times_all = None
    if corr_all:
        times_all = _proc_buffer_n(buf_arr, ndet)
    times = tuple(_proc_buffer(buf_arr[det::ndet]) for det in dets)
    return times_all, times

def proc_buffer(buf, transfer_idx, offset, stride):
    buf_arr = np.array(buf[offset:transfer_idx:stride], dtype=np.int64)
    return _proc_buffer(buf_arr)

@numba.jit(numba.int64[:](numba.int64[:]))
def _proc_buffer(buf):
    times = np.empty(buf.sum(), dtype=np.int64)
    i = 0
    for t, n in enumerate(buf):
        for _ in range(n):
            times[i] = t
            i += 1
    return times

def proc_buffer_n(buf, transfer_idx, ndet):
    buf_arr = np.array(buf[:transfer_idx])
    return _proc_buffer_n(buf_arr, ndet)

@numba.jit(numba.int64[:](numba.int64[:], numba.int64))
def _proc_buffer_n(buf, ndet):
    times = np.empty(buf.sum(), dtype=np.int64)
    i = 0
    for t, n in enumerate(buf):
        tt = t // ndet
        for _ in range(n):
            times[i] = tt
            i += 1
    return times

# ensure _proc_buffer is compiled on import
_buf = np.array([0,0,3,5,0,1], dtype=np.int64)
_out = _proc_buffer(_buf)
_out = _proc_buffer_n(_buf, 1)
del _buf, _out

def correlate(time, clk, det=None, sort='auto', deta=None, detb=None, 
              exp_min=1e-5, exp_max=1, bins_per_decade=5, logspace=None):
    """
    Adaptable correlator function. Finds auto or cross correalation of times,
    and optional det

    Parameters
    ----------
    time : np.ndarray[np.int64]
        Photon arrival times.
    clk : float
        DESCRIPTION.
    det : np.ndarray[np.int32], optional
        Photon detector indexes. If None, using autocorrelation and thus ignored.
        Will produce error is sort is not auto.
        The default is None.
    sort : 'auto', 'cross', optional
        Whether performing auto or cross correlation analysis. The default is 'auto'.
    deta : int | tuple | np.ndarray, optional
        Which detector(s) to analyze auto or cross correlation.
        If None, assuming auto correlation of all photons, or only 2 detector 
        types in cross correlation analysis
        The default is None.
    detb : int | tuple | np.ndarray, optional
        Which detector(s) serving as second set in cross-coorelation analysis. 
        If None, assuming performing auto-correlation, or only 2 detector types
        in cross correlation analysis. The default is None.
    exp_min : TYPE, optional
        DESCRIPTION. The default is 1e-5.
    exp_max : TYPE, optional
        DESCRIPTION. The default is 1.
    bins_per_decade : TYPE, optional
        DESCRIPTION. The default is 5.
    logspace : tuple | dict | np.ndarray, optional
        Overrides exp_min, exp_max and bins_per_decade, if tupel or dict used as
        *args or **kwargs respectively in np.logspace, if np.ndarray, used directly
        as bins for correlate. The default is None.

    Returns
    -------
    bins: np.ndarray[np.float64]
        The bins of the output.
    corr: np.ndarray[np.float64]
        Correlation of inputed data

    """
    # process options for generating bins
    if logspace is None:
        l_min = np.log(exp_min)/np.log(10)
        l_max = np.log(exp_max)/np.log(10)
        bins = np.logspace(l_min, l_max, int(bins_per_decade*int(l_max-l_min)))
    elif not isinstance(logspace, np.ndarray):
        if isinstance(logspace, dict):
            bins = np.logspace(**logspace)
        else:
            bins = np.logspace(*logspace)
    else:
        bins = logspace
    # rescale bins and convert to integer 
    scale_bins = np.round(bins/clk).astype(np.int64)
    scale_bins, index = np.unique(scale_bins, return_index=True)
    bins = bins[index]
    if sort == 'auto':
        if deta is None:
            timea = time
            timeb = time
        else:
            timea = time[_get_mask(det, deta)]
            timeb = timea
    else:
        if deta is None and detb is None:
            deta, detb = np.unique(det)
        timea = time[_get_mask(det, deta)]
        timeb = time[_get_mask(det, detb)]
    return bins, pcorrelate(timea, timeb, scale_bins)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Calculate auto/cross corelation of times")
    parser.add_argument('filename', type=str, help="path to file")
    parser.add_argument('--deta', type=int, help='First index used for cross coorelation')
    parser.add_argument('--detb', type=int, help='Second index used for cross coorelation')
    args = parser.parse_args()
    if args.filename[-3:] == 'csv':
        times, dets, expand_by = load_csv(args.filename)
        clk = 1 / expand_by / config.ACQUISITION_RATE
    else:
        times, dets, clk = load_hdf5(args.filename)
        
    tbins = np.arange(0, times[-1],10000)
    tvals = np.array([((times>=b)*(times<e)).sum() for b, e in zip(tbins[:-1], tbins[1:])])
    pos_time = np.vstack([tbins[:-1], tvals]).T
    bins, corr = correlate(times, clk, dets, 
                           sort='auto' if args.deta is None and args.detb is None else 'cross', 
                           deta=args.deta, detb=args.detb)
    pos_corr = np.vstack([bins[:-1], corr]).T
    
    print(f"begin plotting, {pos_time[:10,:]}")
    canvas = scene.SceneCanvas(keys='interactive', size=(500,400), show=True, fullscreen=False)
    
    grid = canvas.central_widget.add_grid()
    
    line_graph = grid.add_view(row=0, col=1, row_span=10, col_span=15, camera='panzoom', border_color='grey')
    # line_graph.camera.rect = (0,0,500, 400)
    
    line_plot = scene.visuals.Line(pos=pos_time, parent=line_graph.scene, color='g')
    
    line_xax = scene.AxisWidget(orientation='bottom', axis_label="time (s)")
    grid.add_widget(line_xax, 10, 1, 1, 15)
    line_xax.link_view(line_graph)
    
    line_yax = scene.AxisWidget(orientation='left', axis_label="counts")
    grid.add_widget(line_yax, 0, 0, 10, 1)
    line_yax.link_view(line_graph)
    
    corr_graph = grid.add_view(row=10, col=1, row_span=10, col_span=15, camera='panzoom', border_color='g')
    
    logT = scene.Node(parent=corr_graph.scene)
    logT.transform = scene.transforms.LogTransform(base=(10,0,0))
    corr_plot = scene.visuals.Line(pos=pos_corr, parent=logT)
    
    corr_xax = scene.AxisWidget(orientation='bottom', axis_label='G(tau)')
    grid.add_widget(corr_xax, 20, 1, 1, 15)
    corr_xax.link_view(logT)
    
    corr_yax = scene.AxisWidget(orientation='left', axis_label='G(tau)')
    grid.add_widget(corr_yax, 10, 0, 10, 1)
    corr_yax.link_view(corr_graph)
    
    
    # binbox = grid.add_view(name='binbox', pos=(0.0,0.0), size=(0.5,1.0), parent=canvas.scene, camera='panzoom')
    # line2 = scene.visuals.Line(pos=np.vstack([np.arange(0,100,1), np.random.normal(size=100)]), color=0.5*np.ones((corr.size, 4), dtype=np.float32), parent=binbox.scene)
    app.run()
    print(bins)
    print(corr)