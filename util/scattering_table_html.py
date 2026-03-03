from pathlib import Path

import numpy as np
from periodictable.core import default_table, PeriodicTable
from periodictable.nsf import Neutron

# TODO: add a citation column to the html scattering table
def scattering_table_html(path: Path|str|None=None, table: PeriodicTable|None=None) -> str:
    """
    Generate an html table, returning it as a string. If path is given, write the
    html to that path.

    Note: requires the uncertainties package, which is not otherwise required by periodictable.
    """
    from uncertainties import ufloat as U # type: ignore[import-untyped]

    head = """\
<head>
    <meta charset="UTF-8">
    <title>Neutron Cross Sections</title>
    <style>
        table {
            border-collapse: separate;
            border-spacing: 0;
        }
        tbody tr {
            /* This offset ensures the target row isn't hidden behind the sticky header */
            scroll-margin-top: 60px;
        }
        tbody tr:target td,
        tbody tr:has(td:target) td {
            background-color: yellow;
            transition: background-color 2s ease-out;
        }
        tr, td {
            scroll-margin-top: 2em;
        }
        th, td {
            border: 1px solid black;
            padding: 5px;
            border-top: none;
            border-right: none;
        }
        tr:first-child td, tr:first-child th {
            border-top: 1px solid black;
        }
        td:last-child, th:last-child {
            border-right: 1px solid black;
        }
        th {
            position: sticky;
            top: 0;
            background: #e8edf3;
            z-index: 1;
        }
        .centered {
            text-align: center;
        }

    </style>
</head>"""
    table = default_table(table)

    def format_num(re, re_unc, im=None, im_unc=None):
        # Note: using NaN for uncertainty for derived values that should be
        # left blank in the table (currently 191,193Ir cross sections)
        re_str = "" if re is None or np.isnan(re_unc) else f"{U(re, re_unc):fS}" if re_unc else str(re) if re else "0"
        if im is not None:
            im_value = f"{U(abs(im), im_unc):fS}" if im_unc else str(abs(im))
            im_str = f"<br>{'+' if im >= 0 else '–'} {im_value}j"
        else:
            im_str = ""
        return f"{re_str}{im_str}"

    rows = []
    rows.append(f"""
    <tr>
        <th></th>
        <th>Z</th>
        <th>A</th>
        <th>I(π)</th>
        <th>abundance %</th>
        <th>b<sub>c</sub> {Neutron.b_c_units}</th>
        <th>b<sub>+</sub> {Neutron.bp_units}</th>
        <th>b<sub>–</sub> {Neutron.bm_units}</th>
        <th>σ<sub>c</sub> {Neutron.coherent_units}</th>
        <th>σ<sub>i</sub> {Neutron.incoherent_units}</th>
        <th>σ<sub>s</sub> {Neutron.total_units}</th>
        <th>σ<sub>a</sub> {Neutron.absorption_units}</th>
    </tr>""")

    # Generate table rows
    for el in [table.n, *table]:
        element_number = el.number
        isotopes = [iso for iso in el if iso.neutron.absorption is not None or iso.abundance]
        singleton = len(isotopes) == 1
        symbol = el.symbol
        row_id = symbol if symbol != "n" else ""  # Special case for bare neutron
        # print(f"{el=} {A=} {singleton=} {el.neutron.has_sld()=} {[*el]}")
        if element_number <= 96 and not singleton:
            # Multiple isotopes: put element summary above
            n = el.neutron
            rows.append(f"""
    <tr class="element-row" id="{row_id}">
        <td id="{row_id.lower()}">{symbol}</td>
        <td>{element_number}</td>
        <td></td>
        <td></td>
        <td></td>
        <td>{format_num(n.b_c, n.b_c_unc, n.b_c_i, n.b_c_i_unc)}</td>
        <td>{format_num(n.bp, n.bp_unc, n.bp_i, n.bp_i_unc)}</td>
        <td>{format_num(n.bm, n.bm_unc, n.bm_i, n.bm_i_unc)}</td>
        <td>{format_num(n.coherent, n.coherent_unc)}</td>
        <td>{format_num(n.incoherent, n.incoherent_unc)}</td>
        <td>{format_num(n.total, n.total_unc)}</td>
        <td>{format_num(n.absorption, n.absorption_unc)}</td>
    </tr>""")

        for iso in isotopes:
            isotope_number = iso.isotope
            spin = getattr(iso, "nuclear_spin", "")
            n = iso.neutron
            abundance = (
                f"{U(iso.abundance, iso._abundance_unc):fS}" if iso._abundance_unc
                else "100" if iso.abundance == 100.0
                else "" if iso.abundance == 0.0
                else f"{iso.abundance}"
            )
            rows.append(f"""
    <tr{f' class="element-row" id="{row_id}"' if singleton else ''}>
        <td{f' id="{row_id.lower()}"' if singleton else ''}>{symbol if singleton else ''}</td>
        <td>{element_number if singleton else ''}</td>
        <td>{isotope_number}</td>
        <td class="centered">{spin}</td>
        <td>{abundance}</td>
        <td>{format_num(n.b_c, n.b_c_unc, n.b_c_i, n.b_c_i_unc)}</td>
        <td>{format_num(n.bp, n.bp_unc, n.bp_i, n.bp_i_unc)}</td>
        <td>{format_num(n.bm, n.bm_unc, n.bm_i, n.bm_i_unc)}</td>
        <td>{format_num(n.coherent, n.coherent_unc)}</td>
        <td>{format_num(n.incoherent, n.incoherent_unc)}</td>
        <td>{format_num(n.total, n.total_unc)}</td>
        <td>{format_num(n.absorption, n.absorption_unc)}</td>
    </tr>""")

    # Note: don't need \n between rows since we add it to each.
    formatted_table = ''.join(rows)
    html = f"""
<!DOCTYPE html>
<html>
{head}
<body>
<p>Scattering lengths and cross sections for various isotopes evaluated at 2200 m s<sup>–1</sup>
</p>
<table>
{formatted_table}
</table>
<p>This table has been compiled from various sources for the user's convenience and does not represent a critical evaluation by the NIST Center for Neutron Research.
See <a href="https://github.com/python-periodictable/periodictable/blob/master/periodictable/nsf.py">python-periodictable</a> on github for a list of citations.</p>
<p>Natural abundance is from IUPAC Commission on Isotopic Abundances and Atomic Weights (<a href="https://ciaaw.org">CIAAW</a>)</p>
</body>
</html>
"""

    if path:
        # Save the HTML to a file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"HTML table saved to {str(path)}")

    return html

if __name__ == "__main__":
    import sys
    # Example usage: generate the HTML table and save it to a file
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    output_filename = sys.argv[2] if len(sys.argv) > 2 else "scattering_table.html"
    output_path = Path(output_dir) / output_filename
    scattering_table_html(path=output_path)