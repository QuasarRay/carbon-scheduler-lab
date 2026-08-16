import shutil,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agentinfra.bootstrap import BEGIN, BootstrapError, install, uninstall
from agentinfra.transaction import TransactionError

SOURCE=Path(__file__).resolve().parents[2]

class TestBootstrap(unittest.TestCase):
    def _root(self,td):
        r=Path(td);(r/'.agents'/'bootstrap').mkdir(parents=True)
        shutil.copy2(SOURCE/'bootstrap'/'root-AGENTS.block.md',r/'.agents'/'bootstrap'/'root-AGENTS.block.md')
        shutil.copy2(SOURCE/'VERSION',r/'.agents'/'VERSION')
        return r
    def test_preserves_existing_and_roundtrips(self):
        with tempfile.TemporaryDirectory() as td:
            r=self._root(td);before='# Existing project instructions\nKeep me.\n';(r/'AGENTS.md').write_text(before)
            preview=install(r);self.assertFalse(preview['applied']);self.assertTrue(preview['changed'])
            with self.assertRaisesRegex(TransactionError,"governing instruction"):
                install(r,apply=True)
            self.assertEqual((r/'AGENTS.md').read_text(),before)
    def test_clean_install_creates_and_uninstall_removes_root_agents(self):
        with tempfile.TemporaryDirectory() as td:
            r=self._root(td);self.assertFalse((r/'AGENTS.md').exists())
            with self.assertRaisesRegex(TransactionError,"governing instruction"):
                install(r,apply=True)
            self.assertFalse((r/'AGENTS.md').exists())
    def test_unknown_managed_edit_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            r=self._root(td);(r/'AGENTS.md').write_text(f'{BEGIN}\nmanual\n<!-- AEGIS:END -->\n')
            with self.assertRaises(BootstrapError):install(r)
