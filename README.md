# notes
 - installed stm32 tools (flah/debug, zephyr backend)
 - installed zephyr (deps + clone)

```
# deps
sudo apt install --no-install-recommends git cmake ninja-build gperf   ccache dfu-util device-tree-compiler wget python3-dev python3-venv python3-tk   xz-utils file make gcc gcc-multilib g++-multilib libsdl2-dev libmagic1

# from sub zephy folder
python3 -m venv ~/while-true/common/zephyr/.venv

source ~/zephyrproject/.venv/bin/activate
source .venv/bin/activate
pip install west

west init .
# source
west update
# setup zephyr vs build system
west zephyr-export
# west deps
west packages pip --install
west sdk install

west boards
west boards | grep qemu
west boards | grep 767


minicom -b 115200 -D /dev/ttyACM0 

sudo cp /home/bastien/STMicroelectronics/STM32Cube/STM32CubeProgrammer/Drivers/rules/* /etc/udev/rules.d/

west build -p always -b nucleo_f767zi samples/basic/blinky
west flash
west build -p always -b nucleo_f767zi samples/basic/button/
west flash
west build -p always -b nucleo_f767zi samples/basic/threads/
west flash

```