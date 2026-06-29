import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_combat_system.py", "-v", "--tb=short"],
    capture_output=True,
    text=True,
    cwd="/opt/evennia/game",
)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
print("EXIT CODE:", result.returncode)
