# Mantid algorithm profiler
# Copyright (C) 2018 Neil Vaytet & Igor Gudich, European Spallation Source
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import algorithm_tree as at
import numpy as np
import psrecord
import argparse
import copy
import sys


# Parse the logfile outputted by psrecord
def parse_cpu_log(filename):
    rows = []
    dct1 = {}
    dct2 = {}
    start_time = 0.0
    with open(filename, "r") as f:
        for line in f:
            if "#" in line:
                continue
            if "START_TIME:" in line:
                start_time = float(line.split()[1])
                continue
            line = line.replace("[","")
            line = line.replace("]", "")
            line = line.replace("(", "")
            line = line.replace(")", "")
            line = line.replace(",", "")
            line = line.replace("pthread", "")
            line = line.replace("id=", "")
            line = line.replace("user_time=", "")
            line = line.replace("system_time=", "")
            row = []
            lst = line.split()
            for i in range(4):
                row.append(float(lst[i]))
            i = 4
            dct1 = copy.deepcopy(dct2)
            dct2.clear()
            while i < len(lst):
                idx = int(lst[i])
                i += 1
                ut = float(lst[i])
                i += 1
                st = float(lst[i])
                i += 1
                dct2.update({idx: [ut, st]})
            count = 0
            for key, val in dct2.items():
                if key not in dct1.keys():
                    count += 1
                    continue
                elem = dct1[key]
                if val[0] != elem[0] or val[1] != elem[1]:
                    count += 1
            row.append(count)
            row.append(len(dct2))
            rows.append(row)
    return start_time, np.array(rows)


# Convert string to RGB color
# This method is simple but does not guarantee uniqueness of the color.
# It is however random enough for our purposes
def stringToColor(string):

    red = 0
    grn = 0
    blu = 0
    for i in range(0,len(string),3):
        red += ord(string[i])
    for i in range(1,len(string),3):
        grn += ord(string[i])
    for i in range(2,len(string),3):
        blu += ord(string[i])
    red %= 255
    grn %= 255
    blu %= 255
    return [red,grn,blu,(red+grn+blu)/3.0]


# Generate HTML output for a tree node
def treeNodeToHtml(node, lmax, sync_time, header, count, tot_time):

    x0 = ((node.info[1] + header) / 1.0e9) - sync_time
    x1 = ((node.info[2] + header) / 1.0e9) - sync_time
    x2 = 0.5 * (x0 + x1)
    y0 = 0.0
    y1 = -(lmax-node.level+1)
    dt = x1 - x0

    # Get unique color from algorithm name
    color = stringToColor(node.info[0].split(' ')[0])
    # Compute raw time and percentages
    rawTime = dt
    if len(node.children) > 0:
        for ch in node.children:
            rawTime -= (ch.info[2] - ch.info[1]) / 1.0e9
    percTot = dt * 100.0 / tot_time
    percRaw = rawTime * 100.0 / tot_time

    # Create the text inside hover box
    boxText = node.info[0] + " : "
    if dt < 0.1:
        boxText += "%.1E" % dt
    else:
        boxText += "%.1f" % dt
    boxText += "s (%.1f%%) | %.1fs (%.1f%%)<br>" % (percTot,rawTime,percRaw)

    if node.parent is not None:
        boxText += "Parent: " + node.parent.info[0] + "<br>"
    if len(node.children) > 0:
        boxText += "Children: <br>"
        for ch in node.children:
            boxText += "  - " + ch.info[0] + "<br>"

    # Create trace
    base_url = "https://docs.mantidproject.org/nightly/algorithms/"
    outputString = "trace%i = {\n" % count
    outputString += "x: [%f, %f, %f, %f, %f],\n" % (x0, x0, x2, x1, x1)
    outputString += "y: [%f, %f, %f, %f, %f],\n" % (y0, y1, y1, y1, y0)
    outputString += "fill: 'tozeroy',\n"
    outputString += "fillcolor: 'rgb(%i,%i,%i)',\n" % (color[0],color[1],color[2])
    outputString += "line: {\n"
    outputString += "color: '#000000',\n"
    outputString += "dash: 'solid',\n"
    outputString += "shape: 'linear',\n"
    outputString += "width: 1.0\n"
    outputString += "},\n"
    outputString += "mode: 'lines+text',\n"
    # If the background color is too bright, make the font color black.
    # Default font color is white
    if color[3] > 180:
        textcolor = '#000000'
    else:
        textcolor = '#ffffff'
    outputString += "text: ['', '', '<a style=\"text-decoration: none; color: %s;\" href=\"%s%s-v1.html\">%s</a>', '', ''],\n" % (textcolor, base_url, node.info[0].split()[0], node.info[0])
    outputString += "textposition: 'top',\n"
    outputString += "hovertext: '" + boxText + "',\n"
    outputString += "hoverinfo: 'text',\n"
    outputString += "type: 'scatter',\n"
    outputString += "xaxis: 'x',\n"
    outputString += "yaxis: 'y3',\n"
    outputString += "showlegend: false,\n"
    outputString += "};\n"

    return outputString


# Generate HTML interactive plot with Plotly library
def htmlProfile(filename=None, x=None, data=None, records=None, fill_factor=0,
                nthreads=0, lmax=0, sync_time=0, header=None):

    htmlFile = open(filename,'w')
    htmlFile.write("<head>\n")
    htmlFile.write("  <script src=\"https://cdn.plot.ly/plotly-latest.min.js\"></script>\n")
    htmlFile.write("</head>\n")
    htmlFile.write("<body>\n")
    htmlFile.write("  <div id=\"myDiv\"></div>\n")
    htmlFile.write("  <script>\n")
    # CPU
    htmlFile.write("  var trace1 = {\n")
    htmlFile.write("    'x': [\n")
    for i in range(len(x)):
        htmlFile.write("%f,\n" % x[i])
    htmlFile.write("],\n")
    htmlFile.write("    'y': [\n")
    for i in range(len(x)):
        htmlFile.write("%f,\n" % data[i,1])
    htmlFile.write("],\n")
    htmlFile.write("  'xaxis': 'x',\n")
    htmlFile.write("  'yaxis': 'y1',\n")
    htmlFile.write("  type: 'scatter',\n")
    htmlFile.write("  name:'CPU',\n")
    htmlFile.write("};\n")
    # RAM
    htmlFile.write("  var trace2 = {\n")
    htmlFile.write("    x: [\n")
    for i in range(len(x)):
        htmlFile.write("%f,\n" % x[i])
    htmlFile.write("],\n")
    htmlFile.write("    y: [\n")
    for i in range(len(x)):
        htmlFile.write("%f,\n" % (data[i,2]/1000.0))
    htmlFile.write("],\n")
    htmlFile.write("  xaxis: 'x',\n")
    htmlFile.write("  yaxis: 'y2',\n")
    htmlFile.write("  type: 'scatter',\n")
    htmlFile.write("  name:'RAM',\n")
    htmlFile.write("};\n")
    # Active threads
    htmlFile.write("  var trace3 = {\n")
    htmlFile.write("    x: [\n")
    for i in range(len(x)):
        htmlFile.write("%f,\n" % x[i])
    htmlFile.write("],\n")
    htmlFile.write("    y: [\n")
    for i in range(len(x)):
        htmlFile.write("%f,\n" % (data[i,4]*100.0))
    htmlFile.write("],\n")
    htmlFile.write("  xaxis: 'x',\n")
    htmlFile.write("  yaxis: 'y1',\n")
    htmlFile.write("  type: 'scatter',\n")
    htmlFile.write("  name:'Active threads',\n")
    htmlFile.write("};\n")

    count = 4
    dataString = "[trace1,trace2,trace3"
    for tree in at.toTrees(records):
        for node in tree.to_list():
            htmlFile.write(treeNodeToHtml(node, lmax, sync_time, header, count, x[-1]))
            dataString += ",trace%i" % count
            count += 1
    dataString += "]"

    htmlFile.write("var data = " + dataString + ";\n")
    htmlFile.write("var layout = {\n")
    htmlFile.write("  'height': 700,\n")
    htmlFile.write("  'xaxis' : {\n")
    htmlFile.write("    'domain' : [0, 1.0],\n")
    htmlFile.write("    'title' : 'Time (s)',\n")
    htmlFile.write("    'side' : 'top',\n")
    htmlFile.write("  },\n")
    htmlFile.write("  'yaxis1': {\n")
    htmlFile.write("    'domain' : [0.5, 1.0],\n")
    htmlFile.write("    'title': 'CPU (%)',\n")
    htmlFile.write("    'side': 'left',\n")
    htmlFile.write("    'fixedrange': true,\n")
    htmlFile.write("    },\n")
    htmlFile.write("  'yaxis2': {\n")
    htmlFile.write("    'title': 'RAM (GB)',\n")
    htmlFile.write("    'overlaying': 'y1',\n")
    htmlFile.write("    'side': 'right',\n")
    htmlFile.write("    'fixedrange': true,\n")
    htmlFile.write("    'showgrid': false,\n")
    htmlFile.write("    },\n")
    htmlFile.write("  'yaxis3': {\n")
    htmlFile.write("    'domain' : [0, 0.5],\n")
    htmlFile.write("    'anchor' : 'x',\n")
    htmlFile.write("    'showgrid': false,\n")
    htmlFile.write("    'ticks': '',\n")
    htmlFile.write("    'showticklabels': false,\n")
    htmlFile.write("    'fixedrange': true,\n")
    htmlFile.write("    'side': 'left',\n")
    htmlFile.write("    },\n")
    htmlFile.write("  'hovermode' : 'closest',\n")
    htmlFile.write("  'hoverdistance' : 100,\n")
    htmlFile.write("  'legend': {\n")
    htmlFile.write("    'x' : 0,\n")
    htmlFile.write("    'y' : 1.1,\n")
    htmlFile.write("    'orientation' : 'h',\n")
    htmlFile.write("  },\n")
    htmlFile.write("  'annotations': [{\n")
    htmlFile.write("    xref: 'paper',\n")
    htmlFile.write("    yref: 'paper',\n")
    htmlFile.write("    x: 1,\n")
    htmlFile.write("    xanchor: 'right',\n")
    htmlFile.write("    y: 1.1,\n")
    htmlFile.write("    yanchor: 'bottom',\n")
    htmlFile.write("    text: 'Fill factor: %.1f%%',\n" % fill_factor)
    htmlFile.write("    showarrow: false\n")
    htmlFile.write("  }],\n")
    htmlFile.write("  'shapes': [{\n")
    htmlFile.write("      layer: 'below',\n")
    htmlFile.write("      fillcolor: '#E0E0E0',\n")
    htmlFile.write("      line : {\n")
    htmlFile.write("        width: 0,\n")
    htmlFile.write("      },\n")
    htmlFile.write("      x0: 0.0,\n")
    htmlFile.write("      x1: %f,\n" % x[-1])
    htmlFile.write("      y0: 0,\n")
    htmlFile.write("      y1: %i,\n" % (nthreads*100))
    htmlFile.write("      xref: 'x',\n")
    htmlFile.write("      yref: 'y1',\n")
    htmlFile.write("    }],\n")
    htmlFile.write("};\n")
    htmlFile.write("Plotly.newPlot('myDiv', data, layout, {scrollZoom: true});\n")
    htmlFile.write("</script>\n</body>\n</html>\n")
    htmlFile.close()

# Main function to launch process monitor and create interactive HTML plot
def main():

    parser = argparse.ArgumentParser(
        description="Profile a Mantid workflow")

    parser.add_argument("pid", type=str,
                        help="the process id")

    parser.add_argument("--outfile", type=str, default="profile.html",
                        help="name of output html file")

    parser.add_argument("--infile", type=str, default="algotimeregister.out",
                        help="name of input file containing algorithm timings")

    parser.add_argument("--logfile", type=str, default="mantidprofile.txt",
                        help="name of output file containing process monitor data")

    parser.add_argument("--interval", type=float,
                        help="how long to wait between each sample (in "
                             "seconds). By default the process is sampled "
                             "as often as possible.")

    parser.add_argument("--mintime", type=float, default=0.1,
                        help="minimum duration for an algorithm to appear in"
                             "the profiling graph (in seconds).")

    args = parser.parse_args()

    # Launch the process monitor and wait for it to return
    print("Attaching to process " + args.pid)
    psrecord.monitor(int(args.pid), logfile=args.logfile, interval=args.interval)

    # Read in algorithm timing log and build tree
    try:
        header, records = at.fromFile(args.infile)
    except FileNotFoundError:
        raise
    records = [x for x in records if x["finish"] - x["start"] > (args.mintime*1.0e9)]
    # Number of threads allocated to this run
    nthreads = int(header.split()[3])
    # Run start time
    header = int(header.split()[1])
    # Find maximum level in all trees
    lmax = 0
    for tree in at.toTrees(records):
        for node in tree.to_list():
            lmax = max(node.level,lmax)

    # Read in CPU and memory activity log
    try:
        sync_time, data = parse_cpu_log(args.logfile)
    except FileNotFoundError:
        raise

    # Time series
    x = data[:,0]-sync_time

    # Integrate under the curve and compute CPU usage fill factor
    area_under_curve = np.trapz(data[:, 1], x=x)
    fill_factor = area_under_curve / ((x[-1] - x[0]) * nthreads)

    # Create HTML output with Plotly
    htmlProfile(filename=args.outfile, x=x, data=data, records=records,
                fill_factor=fill_factor, nthreads=nthreads, lmax=lmax,
                sync_time=sync_time, header=header)

    return


if __name__ == '__main__':
    sys.exit(main())
