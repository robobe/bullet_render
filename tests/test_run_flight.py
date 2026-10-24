"""Launcher starts the recorder first and drains it after other processes."""
from importlib.util import spec_from_file_location, module_from_spec
from io import StringIO
from pathlib import Path


def test_recorded_launcher_order_logs_and_shutdown(tmp_path,monkeypatch):
    spec=spec_from_file_location('run_flight',Path(__file__).resolve().parents[1]/'tools/run_flight.py')
    module=module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module,'ROOT',tmp_path/'bullet_render')
    monkeypatch.setattr(module.sys,'argv',['run_flight'])
    monkeypatch.setattr(module.signal,'signal',lambda *args:None)
    monkeypatch.setattr(module.time,'sleep',lambda *args:None)
    launched=[]
    killed=[]
    class Process:
        def __init__(self,command,**kwargs):
            self.pid=100+len(launched)
            self.stdout=StringIO('startup diagnostic\n')
            self.returncode=1 if 'examples.external_rc.main' in command else None
            launched.append((command,kwargs))
            if '--ready-file' in command:
                Path(command[command.index('--ready-file')+1]).write_text('ready')
        def poll(self): return self.returncode
        def wait(self,timeout=None): self.returncode=0
    monkeypatch.setattr(module.subprocess,'Popen',Process)
    monkeypatch.setattr(module.os,'killpg',lambda pid,sig:killed.append(pid))
    assert module.main()==1
    assert 'mcap_bagger.cli' in launched[0][0]
    session=next((tmp_path/'bullet_render/recordings').iterdir())
    assert all((session/f'{name}.log').read_text()=='startup diagnostic\n' for name in ('recorder','godot','physics','app'))
    assert launched[0][1]['env']['BULLET_LAUNCH_ID']==session.name
    assert killed[-1]==100
