# mantid-profiler

Use [psrecord](https://github.com/astrofrog/psrecord) and [Plotly.js](https://plot.ly/javascript/) to profile a Mantid workflow.
It monitors CPU and RAM usage and reports the time span of each algorithm (currently, only algorithms are recorded).

## Usage

`python SNSPowderReduction.py & python path/to/mantid-profiler/mantid-profiler.py $!`

## Requires

- psutil

## Results

After running on the `SNSPowderReduction.py` workflow, the profiler produces a `profile.html` file to be viewed with an internet browser.

## Contact

Neil Vaytet, European Spallation Source
