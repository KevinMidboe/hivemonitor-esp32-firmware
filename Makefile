.DEFAULT_GOAL := help

ESP_TOOL := $(shell command -v esptool.py 2> /dev/null)
AMPY := $(shell command -v ampy 2> /dev/null)
devices=$(shell ls /dev/tty.*)
device=

.PHONY: help gateway sender flash

all: esptool-exists ampy-exists
gateway: all upload-gateway ## Upload all gateway files to device
sender: all upload-sender ## Upload all sender files to device
flash: all flash-erase flash-micropython ## Erase and flash firmware to device

esptool-exists:
	@if [ -z $(ESP_TOOL) ]; then echo "esptool.py not found, consider doing 'pip install esptool'"; exit 2; fi

ampy-exists:
	@if [ -z $(AMPY) ]; then echo "ampy not found, consider doing 'pip install ampy'"; exit 2; fi

device-arg-flag-exists:
	@$$(test $(device)) || { \
		echo "No device selected, set 'device=' flag"; \
		echo "Available devices:\n $(devices)\n"; \
		exit 1; \
	}
file-arg-flag-exists:
	@$$(test $(file)) || { \
		echo "No firmware file selected, set 'file=' flag"; \
		exit 2; \
	}

upload-gateway-src:
	@echo "Uploading gateway source files"
	ampy --port $$device put src/gateway.py boot.py
	ampy --port $$device put src/setup/gateway.html index.html

upload-sender-src:
	@echo "Uploading sender source files"
	ampy --port $$device put src/sender.py boot.py
	ampy --port $$device put src/setup/sender.html index.html

upload-shared-files:
	@echo "\nUploading shared files"
	ampy --port $$device put src/setup/styles.css
	ampy --port $$device put src/setup/success.html
	ampy --port $$device put src/setup/configuration_server.py

upload-gateway: device-arg-flag-exists \
	upload-gateway-src \
	upload-shared-files
	@echo "\nReset device using on-board button or Ctrl-D over TTY"

upload-sender: device-arg-flag-exists \
	upload-sender-src \
	upload-shared-files
	@echo "\nReset device using on-board button or Ctrl-D over TTY"

flash-erase: device-arg-flag-exists
	esptool.py --chip esp32 --port $(device) erase_flash

flash-micropython: device-arg-flag-exists file-arg-flag-exists
	esptool.py --chip esp32 --port $(device) write_flash -z 0x1000 $(file)

help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
