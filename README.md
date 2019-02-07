# mantid-profiler

Use [psrecord](https://github.com/astrofrog/psrecord) and [Plotly.js](https://plot.ly/javascript/) to profile a Mantid workflow.

It monitors CPU and RAM usage, and reports the time span of each algorithm (currently, only algorithms are recorded).

## Usage

To profile the `SNSPowderReduction.py` workflow:
```
python SNSPowderReduction.py & python path/to/mantid-profiler/mantid-profiler.py $!
```
The script attaches to the last spawned process, so you can also use the profiler if you are working with `MantidPlot`:
```
./MantidPlot & python path/to/mantid-profiler/mantid-profiler.py $!
```

## Requires

- `psutil`
- You need to build Mantid with the `-DPROFILE_ALGORITHM_LINUX=ON` `CMake` flag to get the timing output from the algorithms.

## Results

After running on the `SNSPowderReduction.py` workflow, the profiler produces a `profile.html` file to be viewed with an internet browser.
![SNS Powder Reduction profile](http://www.nbi.dk/~nvaytet/SNSPowderReduction_12.png)

You can interact with the profile [here](http://www.nbi.dk/~nvaytet/SNSPowderReduction_12.html).

**Controls:**

- Mouse wheel to zoom (horizontal zoom only)
- Left click to select zoom region (horizontal zoom only)
- Double-click to reset axes
- Hold shift and mouse click to pan

## Contact

Neil Vaytet, European Spallation Source
