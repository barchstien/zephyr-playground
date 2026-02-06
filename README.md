# folders
Top folder is an umbrella folder
 - applications/test-app: "Zephyr workspace application"
 - bootloader: added by west MCUboot
 - modules: HAL code, like STM32 (BSD licensed) HW code
 - tools: host tools, TUN scripts, qemu, test apps
 - zephyr: zephyr project, cloned

# TODO
Use STM32 c code (BSD licensed), just like STM HAL code is used in modules/
Make it compile, and add args to select i2c bus and GPIOs
Wrap is with a zephyr driver (known by OS, and takes DT)
Make a DT
Add the driver to my-app, using prj.conf

# dev notes
```sh
from ./application/test-app
west build -p always -b nucleo_f767zi -t flash .

```

# install
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

# clone default repo
west init .
# overwritte zephy and hal_st repos
west init -l app

# source
west update 
west update --narrow -o=--depth=1

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

# HW

## nucleo F767ZI
Set IP/DHCP in prj.conf

## ToF vl53l8
 - using i2c (not SPI)
 - requires FW to be uploaded in boot
 - ensure data returned for pixel is valid
 - pixel data may contain several depth (through glass)
 - pixel data has mouvement detection