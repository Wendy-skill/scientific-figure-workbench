"""Self-test the transparent synthetic demo renderer without network access."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    return subprocess.run([sys.executable, *map(str,args)], cwd=ROOT,
                          capture_output=True, text=True, check=False)


class TestScientificFigureWorkbench(unittest.TestCase):
    def test_full_render_and_independent_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp)
            source=temp/'demo.csv'
            destination=temp/'results'
            demo=run([ROOT/'scripts/make_synthetic_demo.py','--output',source,'--n',180])
            self.assertEqual(demo.returncode,0,demo.stderr)
            rendered=run([ROOT/'scripts/plot_figures.py', '--input',source,
                '--output',destination,'--group','Group','--x','Feature X1',
                '--y','Feature X2','--z','Feature X3','--value','Response Y',
                '--group-order','Control,Treatment','--ylim','0,50'])
            self.assertEqual(rendered.returncode,0,rendered.stderr)
            audited=run([ROOT/'scripts/verify_output.py','--input',source,'--output',destination])
            self.assertEqual(audited.returncode,0,audited.stderr)
            stats=json.loads((destination/'analysis_audit.json').read_text())
            self.assertEqual(stats['source_rows'],360)
            self.assertEqual(stats['groups']['Control']['n'],180)
            self.assertEqual(stats['groups']['Treatment']['n'],180)
            self.assertEqual(stats['source_rows_dropped'],0)

    def test_does_not_silently_clip_or_drop(self):
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp)
            source=temp/'demo.csv'
            self.assertEqual(run([ROOT/'scripts/make_synthetic_demo.py','--output',source]).returncode,0)
            bad_axis=run([ROOT/'scripts/plot_figures.py','--input',source,'--output',temp/'out',
                '--ylim','0,20'])
            self.assertNotEqual(bad_axis.returncode,0)
            self.assertIn('clips',bad_axis.stderr)
            import pandas as pd
            frame=pd.read_csv(source)
            frame.loc[0,'Response Y']=float('nan')
            frame.to_csv(source,index=False)
            bad_input=run([ROOT/'scripts/plot_figures.py','--input',source,'--output',temp/'out'])
            self.assertNotEqual(bad_input.returncode,0)
            self.assertIn('missing values',bad_input.stderr)


if __name__=='__main__':
    unittest.main()