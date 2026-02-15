# LUCID EMPIRE :: Hardware Shield Build
# AUTHORITY: Dva.12 | TITAN V5 FINAL

CC = gcc
CFLAGS = -shared -fPIC -Wall -O2
LDFLAGS = -ldl

LIB_DIR = /opt/lucid-empire/lib
SRC = hardware_shield.c
TARGET = libhardwareshield.so

.PHONY: all install clean

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

install: $(TARGET)
	install -d $(DESTDIR)$(LIB_DIR)
	install -m 755 $(TARGET) $(DESTDIR)$(LIB_DIR)/

clean:
	rm -f $(TARGET)
