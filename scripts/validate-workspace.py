"""Validate coordination without absorbing independent repositories."""
from pathlib import Path
import json
import subprocess

root=Path(__file__).resolve().parents[1]
workspace=json.loads((root/'stir.code-workspace').read_text(encoding='utf-8'))
expected={'stir-workspace':'.','stir-doc':'stir-doc','stir-backend':'stir-backend','stir-frontend':'stir-frontend','stir-main':'stir-main'}
assert {f['name']:f['path'] for f in workspace['folders']}==expected
for name,path in expected.items():
    repo=(root/path).resolve()
    top=Path(subprocess.check_output(['git','-C',str(repo),'rev-parse','--show-toplevel'],text=True).strip()).resolve()
    assert top==repo, f'{name} is not independent'
for child in list(expected)[1:]:
    subprocess.run(['git','-C',str(root),'check-ignore',child+'/README.md'],check=True,stdout=subprocess.DEVNULL)
tracked=subprocess.check_output(['git','-C',str(root),'ls-files','--stage'],text=True)
assert '160000 ' not in tracked
assert not any('/'+child+'/' in tracked or '\t'+child+'/' in tracked for child in list(expected)[1:])
tasks={t['label']:t for t in workspace['tasks']['tasks']}
for action in ['initialize','validate','start','status','smoke','stop']:assert 'STIR: '+action in tasks
for action in ['initialize','start','status','smoke','stop']:assert tasks['STIR: '+action]['options']['cwd']=='${workspaceFolder:stir-main}'
print('PASS: five independent repositories, relative workspace paths/tasks, no child files or gitlinks in parent.')
