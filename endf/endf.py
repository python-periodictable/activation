#!/usr/bin/env python
"""
Run PREPRO filters on ENDF data to define linear interpolation
tables.

See `https://www-nds.iaea.org/public/endf/prepro`_ for details
on the individual programs.  Executables can be downloaded from
there as well.

Once you have downloaded the PREPRO executable, e.g., into
PREPRO12, add this program to the PREPRO binary directory, or set
ENDF_PROGRAMS to the path to the PREPRO directory in this file.

ENDF files can be retrieved from
`https://www-nds.iaea.org/public/download-endf`.
This code was tested with
`https://www-nds.iaea.org/public/download-endf/ENDF-B-VII.1/n-index.htm`.
The program fetch_endf.sh downloads the files and stores them in the
ENDF-B-VII.1 directory.

Each filter takes infile and step as its first two arguments,
returning outfile and step+1.  The outfile name is constructed
by _next_step from the step number and the step name.  If
KEEP_INTERMEDIATES is True, then the name is "STEP-#-name.OUT"
otherwise it is "STEP-0.OUT" or "STEP-1.OUT" alternating.

Run using::

    ./fetch_endf.sh
    mkdir interp
    cd interp
    python ../endf.py ../ENDF-B-VII.1/*.zip

This produces a set of "*.out" files containing the interpolated data.
You can plot individual resonances using, e.g.:

    python ../endf.py --pyplot *Sm-144*.out

The plotter is set to plot the elastic cross section (column 2) and the
capture cross section (column 102). See *ENDF_COLUMNS* for the column names.

To generate the images used on the web modify the code, uncommenting the
lines labeled "For resonance.html". Then run with all interpolated data::

    python ../endf.py --pyplot *

To examine activation cross sections, uncomment "For activation".

Note: ENDF data only roughly corresponds to activation data from calculator.
Even for thermal activation, some reactions in ENDF do not appear in
the activation data table and some reactions in the activation data table do
not appear in ENDF. This is after accounting for stable daughter products
(not listed in activation table) and nuclear isomers (not listed in ENDF?).
For cross sections that appear in both they have approximately the same order
of magnitude, though specific values may differ.
"""
#TODO: Look up the source for tabulated cross sections in the original paper

import sys
import os
import math
import shutil
import zipfile
import glob
import warnings
from pathlib import Path

import numpy as np
from numpy import nan as NaN

try:
    import periodictable as pt
    NEGATIVE_B_C = set(
        f"{el}-{isonum}"
        for el in pt.elements for isonum in el.isotopes for iso in [el[isonum]]
        if iso.neutron.b_c is not None and iso.neutron.b_c < 0)
    #print("b_c is negative for", NEGATIVE_BC)
except ImportError:
    pt = None
    NEGATIVE_B_C = set()
    #warnings.warn(f"periodictable not available so no abundance values")

ROOT = os.path.abspath(os.path.dirname(__file__))
#ENDF_PROGRAMS = os.path.join(ROOT, "PREPRO12")
ENDF_PROGRAMS = os.path.join(ROOT, "MAC")
ENDF_DATA = os.path.join(ROOT,"ENDF-B-VIII.1")
KEEP_INTERMEDIATES = False

# See sec 3.4 and Appendix B of the ENDF manual
# https://www.oecd-nea.org/dbdata/data/endf102.htm#LinkTarget_11914
# https://www.oecd-nea.org/dbdata/data/endf102.htm#LinkTarget_42352
ENDF_COLUMNS = {
    "total": 1, # = 2 + 3
    "coh": 2,
    "nonelastic": 3, # = 4 + a bunch of other stuff
    "inelastic": 4, # = sum (51 to 91)
    "absorption": 27, # = 18 + sum(102 to 117); rarely provided
    "n,2n": 16, # n -> 2n
    "n,3n": 17, # n -> 3n
    "n,na": 22, # n -> n+alpha
    "n,np": 28, # n -> n+proton
    "fission": 18, # =19+20+21+38 [first, second, third, fourth-chance fission]
    "disappearance": 101, # = sum(102 to 117); rarely provided
    # Capture products: 102 to 117
    # gamma, H, D, T, He3, He, 2He 3He - 2H H+He T+2He D+2He H+D H+T D+He
    "n,g": 102, # act
    "n,p": 103, # (n, p)
    "n,d": 104,
    "n,t": 105,
    "n,He3": 106,
    "n,a": 107, # (n, a)
    "n,2a": 108, # (n, 2a)
}
ENDF_LABELS = {v: k for k, v in ENDF_COLUMNS.items()}
# Change in (proton,neutron) count after neutron capture, used to determine
# if the daughter product is stable.
ENDF_DELTA = {
    #xs: (proton, neutron)
    16: (0, -1), # n,2n
    17: (0, -2), # n,3n
    22: (-2, -2), # n,na
    28: (-1, 0), # n,np
    102: (0, 1), # act
    103: (-1, 1), # n,p
    104: (-1, 0), # n,d
    105: (-1, -1), # n,t
    106: (-2, 0), # n,He3
    107: (-2, -1), # n,a
    108: (-4, -3), # n,2a
}

def _next_step(step, name):
    if KEEP_INTERMEDIATES:
        return f"STEP-{step}-{name}.OUT"
    else:
        return f"STEP-{step%2}.OUT", step+1

def _efmt(val,width,digits):
    tens = 0 if val==0 else math.floor(math.log10(abs(val)))
    return "%*.*f%+03d"%(width-3,digits,val/10**tens,tens)

def _run(prog, files):
    if os.system(os.path.join(ENDF_PROGRAMS, prog)) != 0:
        raise RuntimeError(f"error in '{prog}'")
    if not KEEP_INTERMEDIATES:
        for f in files:
            if os.path.exists(f): os.unlink(f)
    print(f":======== Done {prog} ========", file=sys.stderr)

def linear(infile, step, MTs=None):
    """
    run the endf program LINEAR to set up simple linear
    interpolation throughout the entire range

    *MTs* is the list of MTs to interpolate, or None for all.
    """
    outfile, step = _next_step(step, "LINEAR")
    selection_criteria = 0 # 0:MAT, 1:ZA
    monitor = 0 # 0:quiet, 1: noisy
    min_xs = 1e-10 # minimum cross section, or 0 if 1e-10
    keep_points = 1 # 0:keep only interpolated points, 1: keep original and interpolated
    with open("LINEAR.INP","w") as fid:
        fid.write(" %10d%10d%s%10d\n"
                  %(selection_criteria, monitor, _efmt(min_xs,10,4), keep_points))
        fid.write(f"{infile}\n{outfile}\n")
        if MTs:
            for c in MTs:
                fid.write(f"     0 0{c:3d}99999999{c:3d}\n")
        else:
            fid.write("     0 0  099999999999\n") # do everything
        fid.write("""\
                        (BLANK CARD TERMINATES MAT REQUEST RANGES)
 0.00000-00 1.00000-04
                        (BLANK CARD TERMINATES FILE 3 ERROR LAW)
""")
    _run("linear",["LINEAR.INP","LINEAR.LST"])
    return outfile, step

def recent(infile, step, range=None):
    """
    run the endf program RECENT to add resonance effects to the
    cross sections.

    This is only needed for a few cross sections in the thermal
    neutron range.

    *range* is None or [min, max] in eV.  If running ranges in
    sections, always run from lowest to highest.
    """
    outfile, step = _next_step(step, "RESONANCE")
    if range is not None:
        rangestr = _efmt(range[0], 10, 5) + _efmt(range[1], 10, 5)
    else:
        rangestr = ""
    with open("RECENT.INP","w") as fid:
        fid.write(f"""\
          0 1.00000-10          1          1          1          1
{infile}
{outfile}
          1       9999{rangestr}
                        (BLANK CARD TERMINATES MAT REQUEST RANGES)
 0.00000-00 1.00000-04
 1.00000+00 1.00000-04
 2.00000+00 1.00000-03
 2.00000+07 1.00000-03
                        (BLANK CARD TERMINATES FILE 3 ERROR LAW)
""")
    _run("recent", ["RECENT.INP", "RECENT.LST"])
    return outfile, step

def sigma1(infile, step, T=293.6):
    """
    run the endf program SIGMA1 to adjust the temperature of the
    sample, applying doppler broadening to the resonance peaks.
    """
    outfile, step = _next_step(step, "SIGMA1")
    temperature_str = _efmt(T, 10, 5)
    with open("SIGMA1.INP", "w") as fid:
        fid.write(f"""\
          0          0{temperature_str}  1.00000-10          1          0
{infile}
{outfile}
          1       9999
                       (BLANK CARD TERMINATES MAT RANGE REQUESTS)
 0.00000+ 0 1.00000-04
 1.00000+ 0 1.00000-04
 2.00000+ 0 1.00000-03
 2.00000+ 7 1.00000-03
                       (BLANK CARD TERMINATES FILE 3 ERROR LAW)
""")
    _run("sigma1",["SIGMA1.INP", "SIGMA1.LST"])
    return outfile, step

def activate(infile, step):
    """
    run the endf program ACTIVATE to set activation cross sections
    """
    outfile, step = _next_step(step, "ACTIVATE")
    with open("ACTIVATE.INP","w") as fid:
        fid.write(f"{infile}\n{outfile}\n")
    _run("activate", ["ACTIVATE.INP", "ACTIVATE.LST"])
    return outfile, step

def legend(infile, step):
    """
    run the endf program LEGEND to set legendre interpolation
    """
    outfile, step = _next_step(step, "LEGEND")
    with open("LEGEND.INP", "w") as fid:
        fid.write(f"""\
 1.00000-02      20000          2          1          2          0
{infile}
{outfile}
     0 0  0  999999999 0.00000+00 1.00000+09 1.00000-03 1.00000-02
""")
    _run("legend", ["LEGEND.INP", "LEGEND.LST", "LEGEND.TMP"])
    return outfile, step

def fixup(infile, step):
    """
    run the endf program FIXUP to clean up summed columns
    """
    outfile, step = _next_step(step, "FIXUP")
    with open("FIXUP.INP", "w") as fid:
        fid.write(f"""\
10002111111001          (col. 11 = 1 = allow MT reconstruction)
{infile}
{outfile}
 0.0       0.0                  0          0   0  1  (total)
 0.0       0.0                  0          0
 0.0       0.0                  0          0   0  4  (total inelastic)
 0.0       0.0                  0          0
 0.0       0.0                  0          0   0 16  (total n,2n)
 0.0       0.0                  0          0
 0.0       0.0                  0          0   0103  (total n,p)
 0.0       0.0                  0          0
 0.0       0.0                  0          0   0104  (total n,d)
 0.0       0.0                  0          0
 0.0       0.0                  0          0   0105  (total n,t)
 0.0       0.0                  0          0
 0.0       0.0                  0          0   0106  (total n,He-3)
 0.0       0.0                  0          0
 0.0       0.0                  0          0   0107  (total n,alpha)
 0.0       0.0                  0          0
""")

    _run("fixup",["FIXUP.INP","FIXUP.LST"])
    return outfile, step

def dictin(infile, step):
    """
    run DICTIN to update ENDF dictionary
    """
    outfile, step = _next_step(step, "DICTIN")
    with open("DICTIN.INP", "w") as fid:
        fid.write(f"{infile}\n{outfile}\n")
    _run("dictin", ["DICTIN.INP", "DICTIN.LST"])
    return outfile, step

def evalplot(infile):
    shutil.copyfile(os.path.join(ENDF_PROGRAMS,"PLOT.CHR"), "PLOT.CHR")
    shutil.copyfile(os.path.join(ENDF_PROGRAMS,"PLOT.SYM"), "PLOT.SYM")
    shutil.copyfile(os.path.join(ENDF_PROGRAMS,"MT.DAT"), "MT.DAT")
    with open("EVALPLOT.INP", "w") as fid:
        fid.write(f"""\
        0.0       12.5        0.0        2.0          1          1 1.5
{infile}
          0          0          0          0          0 1.00000-08   1
     1 3  1            99999 3999                     1          0

=== This and the below lines are NOT read as input, so you can store ===
=== anything you want below. Here I have defined how the input data  ===
=== is interpreted = so you know what each input field means.        ===
------------------------------------------------------------------------
 Description of Plotter and Plots per Frame
 -----------------------------------------------------------------------
 X Dimensions (X-Min to X-Max)-----------------     0.0000 to     13.500
 Y Dimensions (Y-Min to Y-Max)-----------------     0.0000 to     10.000
 Layout of Plots per Frame (X by Y)------------          1 by 1
 Character Size Multiplier---------------------       1.50
 -----------------------------------------------------------------------
 ENDF/B Data Filename
------------------------------------------------------------------------
 EVALPLOT.IN
 -----------------------------------------------------------------------
 -----------------------------------------------------------------------
 Input Parameters
 -----------------------------------------------------------------------
 Retrieval Criteria----------------------------        MAT
 Grid Type-------------------------------------Tick Marks
 Should Border be Plotted on Each Plot---------         No
 Line Thickness--------------------------------          0
 Cross Section Temperature on Plots------------        Yes
 Mimimum Ratio of Y Min to Max Range of Plot--- 1.00000-08
 On Screen Background Color--------------------White
 -----------------------------------------------------------------------
 Request Ranges
 -----------------------------------------------------------------------
         Mimimum                      Maximum
    MAT MF  MT Energy-eV         MAT MF  MT Energy-eV    Type
 -----------------------------------------------------------------------
      1  3   1 0.00000+ 0      99999  3 999 0.00000+ 0      0
 -----------------------------------------------------------------------
""")

    _run("evalplot", ["EVALPLOT.INP", "EVALPLOT.LST", "PLOT.CHR", "PLOT.SYM", "MT.DAT"])

def endf_read1d(head, fid):
    # skip two tab records
    line1 = fid.readline()
    line2 = fid.readline()
    num_pairs = int(line1[55:66])

    pairs = []
    while fid:
        line = fid.readline()
        #print line[:-1]
        col = [line[0:11], line[11:22], line[22:33],
                line[33:44], line[44:55], line[55:66]]
        if num_pairs >= 3:
            pairs.extend([(float(col[0]), float(col[1])),
                          (float(col[2]), float(col[3])),
                          (float(col[4]), float(col[5]))])
            num_pairs -= 3
            if num_pairs == 0: break
        elif num_pairs == 2:
            pairs.extend([(float(col[0]), float(col[1])),
                          (float(col[2]), float(col[3]))])
            break
        elif num_pairs == 1:
            pairs.extend([(float(col[0]), float(col[1]))])
            break
    line = fid.readline() # skip the "SEND" record
    return [np.array(v) for v in zip(*pairs)]

def endf_load(infile, columns):
    result = {}
    with open(infile, "r") as fid:
        while True:
            line = fid.readline()
            if line == "": break
            # TODO: if asking for 101, then add 102 through 117
            #ns = int(line[75:80])) # sequence number
            if line[70:75] in columns:
                mat = int(line[66:70]) #material code
                mf = int(line[70:72])
                mt = int(line[72:75])
                result[(mat, mf, mt)] = endf_read1d(line, fid)
    return result

def select(x,y,lo,hi):
    idx = (x>=lo) & (x<=hi)
    #print "selected", x[idx]
    return x[idx], y[idx]

def xs_table(infile, columns):
    """
    Load the linear interpolation tables for a list of cross section.
    """
    items = [f" 3{c:3d}" for c in columns]
    data = endf_load(infile, items)
    data = dict((k[2], v) for k, v in data.items())
    if not data:
        return None
    #print infile,[v[0].shape for v in data.values()]
    x = np.unique(np.hstack(tuple(v[0] for v in data.values())))
    #print "x",x
    ypairs = [
        (data[c] if c in data and len(data[c][0]) > 0 else ((x.min(), x.max()), (NaN, NaN)))
        for c in columns
        ]
    table = np.array([x] + [np.interp(x, v[0], v[1]) for v in ypairs])
    return table

def save_table(outfile, table, range=None):
    if range:
        x = table[0,:]
        idx = (x>=range[0])&(x<=range[1])
        table = table[:,idx]
    np.savetxt(outfile, table.T)

def expand_zip(infile):
    archive = zipfile.ZipFile(infile)
    members = archive.infolist()
    if len(members) != 1:
        archive.close()
        raise RuntimeError(f"Too many entries in '{infile}'")
    archive.extract(members[0])
    archive.close()
    return members[0].filename

def isotope_id(filename):
    """
    Parse filename into (symbol, isotope).

    Symbol is a one or two letter string. Isotope is a number, possibly
    with a trailing M for nuclear isomers.

    ENDF-B-VII.1
        n_6152_61-Pm-148.out
        n_6153_61-Pm-148M.out  # nuclear isomer
    ENDF-B-VIII.1
        n_061-Pm-148_6152.out
        n_061-Pm-148M_6153.out  # nuclear isomer
    """
    try:
        name = Path(filename).stem
        _, symbol, iso = name.split('-')
        iso = iso.split('_')[0]
        return symbol, iso
    except Exception:
        raise RuntimeError(f"Could not extract -El-### from {filename}")

# red   green   yellow   blue   magenta  cyan  gray
colors = ["#"+c for c in """
ff0000  00ff00  e4e400  b0b0ff  ff00ff  00ffff  b0b0b0
b00000  00b000  baba00  8484ff  b000b0  00b0b0  848484
870000  008700  878700  4949ff  870087  008787  494949
550000  005500  545400  0000ff  550055  005555  000000
""".split()]
del colors[7:21]  # remove second & third row
del colors[7:] # remove fourth row
del colors[6::7]  # remove gray
lines = ["-", "--", "-.", ":"]

_w2e_conversion = 81.80420235572412/1e3
def wavelength(eV):
    return np.sqrt(_w2e_conversion/eV)

def w2e(L):
    return _w2e_conversion/L**2

# Line positions Angstroms to eV
L0p1  = 8180.420*1e-3
L0p2  = 2045.105*1e-3
L0p5  = 327.2168*1e-3
V2200 = 25.29886*1e-3
L5    = 3.272168*1e-3
L6    = 2.272339*1e-3
L15   = 0.3635742*1e-3
L20   = 0.2045105*1e-3

FIGURES = [] # [fig, ...]
LINENUM = -1 # int
ISO_COLOR = {} # {f: fig}
_yrange = [np.inf, -np.inf]
_xlim = None
#_xlim = [0.51, 12]
def iso_color(f):
    import matplotlib.pyplot as plt
    global LINENUM
    num_colors = len(colors)
    if f not in ISO_COLOR:
        first = LINENUM < 0
        LINENUM += 1
        cycle = LINENUM%num_colors
        if cycle == 0 and not first:
            showplot(show=False)
            _yrange[:] = [np.inf, -np.inf]
        if cycle == 0:
            if not first:
                FIGURES.append(plt.gcf())
            plt.figure(figsize=(18, 3), tight_layout={'pad': 0})
            plt.subplot2grid((1, 5), (0, 0), colspan=4)
            #pylab.figure(figsize=(8,2.3), tight_layout={'pad':0})
            #pylab.subplot2grid((1,3),(0,0),colspan=2)
        ISO_COLOR[f] = colors[cycle]
    return ISO_COLOR[f]

_first_row = True
def pyplot(
        f, table, columns, resonance, 
        E_cutoff=None, active_only=False,
        x_data="energy", y_data="cross section",
        plot=True):
    import matplotlib.pyplot as plt
    first = LINENUM < 0

    #print "shape",table.shape
    el, iso = isotope_id(f)
    name = f"{el}-{iso}"
    p = abundance(f)  # isotope abundance
    tag = f" ({p:.1f}%)" if p>0 and pt is not None else ""
    #label += " res: %.2fA"%wavelength(resonance)
    x = table[0, :]
    index = slice(None) if E_cutoff is None else (x < E_cutoff)
    for k, ck in enumerate(columns):
        xs = ENDF_LABELS[ck]
        y = table[k+1, :]
        if not (y[index] > 1e-9).any():
            continue  # Skip empty cross sections
        if xs in ("elastic", "coh"):
            b_c_sign = -1.0 if name in NEGATIVE_B_C else 1.0
            sl = b_c_sign*np.sqrt(100*y/(4*np.pi))
        else:
            sl = y / (2000*wavelength(x))
        capture_abundance = abundance(f, ck)  # daughter product abundance
        if active_only and capture_abundance > 0:
            print("skipping", ck)
            continue # Skip stable daughter products


        # One or the other table
        #keep = resonance_table(name, p, x, sl)
        keep = energy_dep_table(name, p, xs, x, sl)

        if plot and keep:
            # Transform x, y if desired
            wl = wavelength(x)
            xp = x if x_data == "energy" else wl
            yp = sl if y_data == "scattering length" else y
            if _xlim is not None:
                index = (wl >= _xlim[0]) & (wl <= _xlim[1])
                ymin, ymax = yp[index].min(), yp[index].max()
                _yrange[:] = min(_yrange[0], ymin), max(_yrange[1], ymax)
            if 0: #absolute
                plt.loglog(
                    xp, yp,
                    label=f"{name}{tag} {xs}",
                    linestyle=lines[k%len(lines)],
                    color=iso_color(f),
                )
            else: # change
                if xs in ("elastic", "coh") and y_data == "scattering length":
                    y0 = np.sqrt(np.interp(V2200, x, yp**2))
                else:
                    y0 = np.interp(V2200, x, yp)
                plt.plot(
                    #xp, (yp-y0)/y0, # relative change
                    xp, (yp - y0), # absolute change
                    label=f"{name}{tag} {xs}",
                    linestyle=lines[k%len(lines)],
                    color=iso_color(f),
                )
            # label='_nolegend_'

def energy_dep_table(iso, abundance, xs, x, y):
    """Table of relative total cross section"""
    global _first_row
    L = [0.5, 2, 4, 6, 8, 10, 12]
    TARGETS = [V2200, *(w2e(Lk) for Lk in L)]
    if xs in ("elastic", "coh"):
        yp = np.sqrt(np.interp(TARGETS, x, y**2))
    else:
        yp = np.interp(TARGETS, x, y)
    change = yp[1:] - yp[0]
    percent_change = 100*change/yp[0]
    # sld_change = 10 Nb Δb_c, with median number density 0.0386 / Å³
    #if (0.4*abs(change)*abundance/100 < 0.2).all(): return False
    #if (0.4*abs(change) < 0.2).all(): return False
    #if abs(yp[0]) < 1e-3 or (abs(percent_change) < 10).all() or abundance < 5: return False
    if _first_row:
        print("Table of scattering lengths by isotope and interaction")
        print("%7s %7s %7s %7s" % (
            "isotope",
            "abund.",
            "scatlen",
            "thermal"),
            " ".join(f"{Lk:6.1f}Å" for Lk in L)  # % change
            #" ".join("%7s"%(f"Δ@{Lk:.1f}Å") for Lk in L)  # abs change
            )
        _first_row = False
    print(
        "%7s"%iso,
        "%7s"%(f"{abundance:.1f}%" if abundance > 0 else "-"),
        "%7s"%xs,
        "%7.3f"%yp[0],
        " ".join("%6.1f%%"%vi for vi in percent_change), # % change
        #" ".join("%7.3f"%vi for vi in change), # abs change
        )
    return True

def resonance_table(iso, abundance, resonance):
    global _first_row
    if _first_row:
        print("Table of resonance onsets")
        print("%7s %7s %7s %9s" % ("isotope", "abund.", "λ (Å)", "E (meV)"))
        _first_row = False
    print("%7s %7s %7.2f %9.2f"%(
        iso,
        f"{abundance:.1f}%" if abundance > 0 else "-",
        wavelength(resonance),
        resonance*1e3),
        )
    return True


def showplot(x_data="energy", y_data="cross section", show=True):
    import pylab
    from matplotlib import transforms as mtransforms
    pylab.grid(True)
    # Axis limits, or none for auto range
    #pylab.axis([5e0,20e3,1e-1,9e3]) # For resonances.html
    #pylab.axis([1e-2,10e3,1e-1,5e3])
    #pylab.axis([1e1,1e8,1e-6,1e2]) # For epithermal
    #pylab.axis([5e0,1e8,1e-1,9e3]) # For full range
    pylab.title('Elastic scattering from ENDF/B-VII.1 nuclear database')
    xlabel = 'Energy (eV)' if x_data == "energy" else 'Wavelength (Å)'
    ylabel = 'Cross section (barns)' if y_data == "cross section" else 'Scattering length (fm)'
    pylab.xlabel(xlabel)
    #pylab.gca().set_xticklabels([])
    pylab.ylabel(ylabel)
    #pylab.xscale('linear')
    #pylab.yscale('linear')
    pylab.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax = pylab.gca()
    trans = mtransforms.blended_transform_factory(
        ax.transData, ax.transAxes)
    pylab.xscale('linear')
    pylab.yscale('linear')
    if _xlim is not None:
        pylab.xlim(*_xlim)
        window = (_yrange[1] - _yrange[0])*0.05
        #pylab.ylim(_yrange[0]-window, _yrange[1]+window)
    for E,L in (L20,20),(L6,6),(V2200,1.78),(L0p5,0.5),(L0p1,0.1):
    #for E,L in (V2200,1.78),(L0p5,0.5),(L0p1,0.1):
    #if False:
        xp = E if x_data == "energy" else L
        pylab.axvline(xp)
        if _xlim and (L < _xlim[0] or L > _xlim[1]): continue
        pylab.text(xp,0.05,'%g A'%L,transform=trans)
    if show:
        FIGURES.append(pylab.gcf())
        #for i,h in enumerate(FIGURES): h.savefig('figure_%d.png'%(i+1))
        pylab.show()

def run_endf(infile, outfile=None):
    out, step = infile, 1
    if '.' not in infile: # isotope
        #if not outfile:
        #    outfile = infile+".out"
        pattern = os.path.join(ENDF_DATA, f"*-{infile}.zip")
        match = list(glob.glob(pattern))
        if len(match) != 1:
            raise RuntimeError(f"'{infile}' is not an isotope")
        infile = match[0]
    if outfile is None:
        outfile = os.path.splitext(os.path.basename(infile))[0]+".out"
    if os.path.exists(outfile):
        print(f"{outfile} already exists...skipping")
        return
    if infile.endswith('.zip'):
        out = "STEP-0.OUT"
        zipname = expand_zip(infile)
        os.rename(zipname,out)
    out,step = linear(out, step)  # must be first
    out,step = recent(out, step)  # add resonances
    out,step = sigma1(out, step, 293.16) # set temperature to 20 C
    out,step = activate(out, step)
    #out,step = legend(out, step)
    #out,step = sixpak(out, step)
    #out,step = spectra(out, step)
    out,step = fixup(out, step)
    out,step = dictin(out, step)
    os.rename(out, outfile)
    for step in (0, 1):
        if os.path.exists(f"STEP-{step}.OUT"):
           os.unlink(f"STEP-{step}.OUT")
    return outfile

def first_resonance(table, col):
    # 20 A => 0.2 meV; 0.1 A => 8180 meV
    # Arcs: 1500, Sequoia: 2000, Vision: 1000, Powgen, Nomad: 8180
    slope = np.diff(table[col,:])/np.diff(table[0,:])
    #import pylab
    #pylab.semilogx(table[0,lo:hi-1],slope,table[0,lo:hi-2],np.diff(slope))
    #pylab.figure()
    #print slope.max(),slope.min(),np.diff(slope).max(),np.diff(slope).min()
    #print "f'",slope[slope>0.1]
    #print "f''",np.diff(slope)[np.diff(slope)<-0.1]
    up = np.where(slope > 0.2)[0]
    down = np.where(np.diff(slope) < -0.2)[0]
    if len(up) == 0 and len(down) == 0:
        return table[0, -1]
    elif len(up) == 0:
        return table[0, down[0]]
    elif len(down) == 0:
        return table[0, up[0]]
    else:
        return table[0, min(up[0], down[0])]

def abundance(filename, xs=-1):
    """
    Return abundance of element given in endf output file, for example
    'n_6152_61-Pm-148.out'. If xs is given, then return the abundance
    of the element after neutron capture. For example, xs=102 is for n,g
    neutron capture. See ENDF_COLUMNS for the cross section numbers.
    """
    el, iso = isotope_id(filename)
    if iso.endswith('M'):
        return 0 # nuclear isomers have no natural abundance (?)
    z = pt.elements.symbol(el).number
    n = int(iso.rstrip('M')) - z
    # Get change in proton and neutron count for the daughter product of the
    # capture, or (0,0) for parent if not looking at a capture cross section.
    dp, dn = ENDF_DELTA.get(xs, (0,0))
    try:
        daughter = pt.elements[z + dp][z + dp + n + dn]
        #if dp or dn:
        #    parent = pt.elements[z][z + n]
        #    print(f"{parent} {ENDF_LABELS[xs]} -> {daughter} [{daughter.abundance*100:.1f}%]")
        return daughter.abundance
    except KeyError:
        return 0

def cmd_show_interp(files, plot=True):
    import sys
    # TODO: Convert runtime flags into command line options
    #x_data = "energy"
    #y_data = "cross section"
    x_data = "wavelength"
    y_data = "scattering length"
    E_cutoff = None # show all curves with significant XS
    E_cutoff = 1 # [eV] For resonance.html and activation show curves with significant XS below E
    active_only = True # For activation
    active_only = False # For resonances.html, show all cross sections
    natural_only = True # For resonances.html activation only naturally occurring isotopes
    common_only = False # Only common isotopes
    thermal_resonance = False # For resonances.html, only consider thermal resonances

    #columns = [1,2,3,4,102,103,104,105,106,107]
    #columns = [1,2,102,107] # total coh act n,a
    #columns = [1] # total cross section
    #columns = [2] # For resonances.html, show elastic cross sections
    #columns = [102] #    act
    #columns = [107] # n,a
    #columns = [16, 102, 103, 107] # For activation: n,2n act n,p n,a
    columns = [2, 102, 103, 107, 16] # coh act n,p n,a n,2n

    if (common_only or natural_only) and pt is None:
        print("Need periodictable to evaluate isotope abundance")
        sys.exit(1)

    for f in files:
        #if '*' in f or "-O-" in f:
        #    print(f"no data for {f}")
        #    continue
        p = abundance(f)
        if (common_only and p < 0.1) or (natural_only and p <=0):
            continue
        table = xs_table(f, columns)
        #save_table(os.path.splitext(f)[0]+".tab", table, range=(1e0,1e2))
        if table is not None:
            # Only plot isotopes with thermal resonance
            res = first_resonance(table, 1)
            if thermal_resonance and res > L0p1:
                continue
            # plot using matplotlib
            pyplot(
                f, table, columns, res, E_cutoff=E_cutoff,
                active_only=active_only, x_data=x_data, y_data=y_data,
                plot=plot)
    if plot and LINENUM >= 0:
        showplot(x_data, y_data)

def cmd_interp(files):
    """Convert endf data to plottable columns"""
    for f in files:
        try:
            run_endf(f)
        except Exception as e:
            print(f"when processing {f}:\n   {e}")

def cmd_endf_plot(files):
    """plot using endf program"""
    #KEEP_INTERMEDIATES = True
    for f in sys.argv[2:]:
        evalplot(f)

if __name__ == "__main__":
    import sys
    if sys.argv[1] == "--endfplot":
        cmd_endf_plot(sys.argv[2:])
    elif sys.argv[1] in ("--table", "--noplot", "--pyplot", "--plot"):
        plot = sys.argv[1] in ("--pyplot", "--plot")
        cmd_show_interp(sys.argv[2:], plot=plot)
    elif sys.argv[1] == "--interp":
        cmd_interp(sys.argv[2:])
    else:
        cmd_show_interp(sys.argv[1:], plot=True)
