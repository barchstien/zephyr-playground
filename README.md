# folders
 - top folder: git, venv and west
 - zephyr: zephyr project, cloned
 - applications/test-app: "Zephyr workspace application"

# test-app
```sh
from ./application/test-app
west build -p always -b nucleo_f767zi -t flash .

```

# notes
 - installed stm32 tools (flah/debug, zephyr backend)
 - installed zephyr (deps + clone)

https://docs.zephyrproject.org/latest/boards/st/nucleo_f767zi/doc/index.html

https://docs.zephyrproject.org/latest/develop/getting_started/index.html
```
# deps
sudo apt install --no-install-recommends git cmake ninja-build gperf   ccache dfu-util device-tree-compiler wget python3-dev python3-venv python3-tk   xz-utils file make gcc gcc-multilib g++-multilib libsdl2-dev libmagic1

# from sub zephy folder
python3 -m venv ./.venv
source .venv/bin/activate
pip install west

west init .
# source
west update
# cmake
west zephyr-export
# west deps
west packages pip --install
west sdk install

west boards
west boards | grep qemu
west boards | grep 767


minicom -b 115200 -D /dev/ttyACM0 

# to access as non-root user
sudo cp /home/bastien/STMicroelectronics/STM32Cube/STM32CubeProgrammer/Drivers/rules/* /etc/udev/rules.d/

west build -p always -b nucleo_f767zi samples/basic/blinky
west flash
west build -p always -b nucleo_f767zi samples/basic/button/
west flash
west build -p always -b nucleo_f767zi samples/basic/threads/
west flash

```