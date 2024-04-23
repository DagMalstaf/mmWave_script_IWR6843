from lupa import LuaRuntime
import os
import subprocess
import time

def start_mmwave_studio_with_scripts():
    cmd_path = r'C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\RunTime\RunCustomScripts.cmd'
    studio_runtime_path = r'C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\RunTime'

    subprocess.Popen(cmd_path, cwd=studio_runtime_path)
    
    time.sleep(200) 
 

def execute_lua_scripts(script_paths):
    lua = LuaRuntime(unpack_returned_tuples=True)

    for script_path in script_paths:
        try:
            with open(script_path, 'r') as file:
                lua_script = file.read()
            lua.execute(lua_script)
            print(f"Successfully executed: {script_path}")
        except IOError as e:
            print(f"Failed to read the script file {script_path}: {e}")
            return
        except Exception as e:
            print(f"Error executing Lua script {script_path}: {e}")
            return

def main():
    script_paths = [
        r'C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\Scripts\AR1xInit.lua',
        r'C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\Scripts\Startup.lua',
    ]
    
    #execute_lua_scripts(script_paths)

    start_mmwave_studio_with_scripts()
    


if __name__ == "__main__":
    main()






