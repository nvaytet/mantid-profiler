# Copyright (c) 2013, Thomas P. Robitaille
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
###############################################################################
#
# 2018: Modified for Mantid profiler by Neil Vaytet & Igor Gudich
#
###############################################################################

from __future__ import (unicode_literals, division, print_function,
                        absolute_import)

import time


# returns percentage for system + user time
def get_percent(process):
    try:
        return process.cpu_percent()
    except AttributeError:
        return process.get_cpu_percent()


def get_memory(process):
    try:
        return process.memory_info()
    except AttributeError:
        return process.get_memory_info()


def get_threads(process):
    try:
        return process.threads()
    except AttributeError:
        return process.get_threads()


def all_children(pr):
    try:
        return pr.children(recursive=True)
    except AttributeError:
        return pr.get_children(recursive=True)
    except Exception:  # pragma: no cover
        return []


def update_children(old_children, new_children): # old children - dict, new_children - list
    new_dct = {}
    for ch in new_children:
        new_dct.update({ch.pid : ch})

    todel = []
    for pid in old_children.keys():
        if pid not in new_dct.keys():
            todel.append(pid)

    for pid in todel:
        del old_children[pid]

    updct = {}
    for pid in new_dct.keys():
        if pid not in old_children.keys():
            updct.update({pid: new_dct[pid]})
    old_children.update(updct)


def monitor(pid, logfile=None, interval=None):

    # We import psutil here so that the module can be imported even if psutil
    # is not present (for example if accessing the version)
    import psutil

    pr = psutil.Process(pid)

    # Record start time
    starting_point = time.time()
    try:
        start_time = time.perf_counter()
    except AttributeError:
        start_time = time.time()

    f = open(logfile, 'w')
    f.write("# {0:12s} {1:12s} {2:12s} {3:12s} {4}\n".format(
        'Elapsed time'.center(12),
        'CPU (%)'.center(12),
        'Real (MB)'.center(12),
        'Virtual (MB)'.center(12),
        'Threads info'.center(12))
    )
    f.write('START_TIME: {}\n'.format(starting_point))

    children = {}
    for ch in all_children(pr):
        children.update({ch.pid: ch})

    try:

        # Start main event loop
        while True:

            # Find current time
            try:
                current_time = time.perf_counter()
            except AttributeError:
                current_time = time.time()

            try:
                pr_status = pr.status()
            except TypeError:  # psutil < 2.0
                pr_status = pr.status
            except psutil.NoSuchProcess:  # pragma: no cover
                break

            # Check if process status indicates we should exit
            if pr_status in [psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD]:
                print("Process finished ({0:.2f} seconds)"
                      .format(current_time - start_time))
                break

            # Get current CPU and memory
            try:
                current_cpu = get_percent(pr)
                current_mem = get_memory(pr)
                current_threads = get_threads(pr)
            except Exception:
                break
            current_mem_real = current_mem.rss / 1024. ** 2
            current_mem_virtual = current_mem.vms / 1024. ** 2

            # Get information for children
            update_children(children, all_children(pr))
            for key, child in children.items():
                try:
                    current_cpu += get_percent(child)
                    current_mem = get_memory(child)
                    current_threads.extend(get_threads(child))
                except Exception:
                    continue
                current_mem_real += current_mem.rss / 1024. ** 2
                current_mem_virtual += current_mem.vms / 1024. ** 2

            f.write("{0:12.6f} {1:12.3f} {2:12.3f} {3:12.3f} {4}\n".format(
                current_time - start_time + starting_point,
                current_cpu,
                current_mem_real,
                current_mem_virtual,
                current_threads))
            f.flush()

            if interval is not None:
                time.sleep(interval)

    except KeyboardInterrupt:  # pragma: no cover
        pass

    if logfile:
        f.close()
