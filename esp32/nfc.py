"""RC522 NFC reader/writer for MicroPython on ESP32.

Wiring (RC522 → ESP32):
  SDA  → GPIO 5
  SCK  → GPIO 18
  MOSI → GPIO 23
  MISO → GPIO 19
  RST  → GPIO 22
  3.3V → 3.3V
  GND  → GND
"""

from machine import Pin, SPI


class RC522:
    """Minimal MFRC522/RC522 driver for reading/writing NTAG213 tags."""

    # RC522 registers
    CommandReg = 0x01
    ComIEnReg = 0x02
    ComIrqReg = 0x04
    DivIrqReg = 0x05
    ErrorReg = 0x06
    FIFODataReg = 0x09
    FIFOLevelReg = 0x0A
    ControlReg = 0x0C
    BitFramingReg = 0x0D
    CollReg = 0x0E
    ModeReg = 0x11
    TxControlReg = 0x14
    TxASKReg = 0x15
    CRCResultRegL = 0x21
    CRCResultRegH = 0x22
    TModeReg = 0x2A
    TPrescalerReg = 0x2B
    TReloadRegH = 0x2C
    TReloadRegL = 0x2D
    VersionReg = 0x37

    # Commands
    Idle = 0x00
    CalcCRC = 0x03
    Transceive = 0x0C
    MFAuthent = 0x0E
    SoftReset = 0x0F

    # PICC commands
    REQIDL = 0x26
    REQALL = 0x52
    ANTICOLL1 = 0x93
    ANTICOLL2 = 0x95
    SELECT1 = 0x93
    SELECT2 = 0x95
    READ = 0x30
    WRITE = 0xA2  # NTAG write (4 bytes per page)

    def __init__(self, sck=18, mosi=23, miso=19, sda=5, rst=22):
        self.sda = Pin(sda, Pin.OUT)
        self.rst = Pin(rst, Pin.OUT)
        self.rst.value(1)
        self.sda.value(1)
        self.spi = SPI(2, baudrate=1000000, polarity=0, phase=0,
                       sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
        self._init_rc522()

    def _write_reg(self, reg, val):
        self.sda.value(0)
        self.spi.write(bytearray([(reg << 1) & 0x7E, val]))
        self.sda.value(1)

    def _read_reg(self, reg):
        self.sda.value(0)
        self.spi.write(bytearray([((reg << 1) & 0x7E) | 0x80]))
        val = self.spi.read(1)
        self.sda.value(1)
        return val[0]

    def _set_bit(self, reg, mask):
        self._write_reg(reg, self._read_reg(reg) | mask)

    def _clear_bit(self, reg, mask):
        self._write_reg(reg, self._read_reg(reg) & (~mask))

    def _init_rc522(self):
        self._write_reg(self.CommandReg, self.SoftReset)
        import time
        time.sleep_ms(50)
        self._write_reg(self.TModeReg, 0x8D)
        self._write_reg(self.TPrescalerReg, 0x3E)
        self._write_reg(self.TReloadRegL, 30)
        self._write_reg(self.TReloadRegH, 0)
        self._write_reg(self.TxASKReg, 0x40)
        self._write_reg(self.ModeReg, 0x3D)
        self._antenna_on()

    def _antenna_on(self):
        if ~(self._read_reg(self.TxControlReg)) & 0x03:
            self._set_bit(self.TxControlReg, 0x03)

    def _communicate(self, command, data):
        irq_en = 0x00
        wait_irq = 0x00
        if command == self.Transceive:
            irq_en = 0x77
            wait_irq = 0x30

        self._write_reg(self.ComIEnReg, irq_en | 0x80)
        self._clear_bit(self.ComIrqReg, 0x80)
        self._set_bit(self.FIFOLevelReg, 0x80)
        self._write_reg(self.CommandReg, self.Idle)

        for b in data:
            self._write_reg(self.FIFODataReg, b)

        self._write_reg(self.CommandReg, command)
        if command == self.Transceive:
            self._set_bit(self.BitFramingReg, 0x80)

        i = 2000
        while True:
            n = self._read_reg(self.ComIrqReg)
            i -= 1
            if n & wait_irq:
                break
            if n & 0x01:
                return None, 0
            if i == 0:
                return None, 0

        self._clear_bit(self.BitFramingReg, 0x80)
        if self._read_reg(self.ErrorReg) & 0x1B:
            return None, 0

        back_len = self._read_reg(self.FIFOLevelReg)
        back_data = []
        for _ in range(back_len):
            back_data.append(self._read_reg(self.FIFODataReg))

        return back_data, back_len

    def _crc(self, data):
        self._clear_bit(self.DivIrqReg, 0x04)
        self._set_bit(self.FIFOLevelReg, 0x80)
        for b in data:
            self._write_reg(self.FIFODataReg, b)
        self._write_reg(self.CommandReg, self.CalcCRC)
        i = 255
        while True:
            n = self._read_reg(self.DivIrqReg)
            i -= 1
            if n & 0x04:
                break
            if i == 0:
                break
        return [self._read_reg(self.CRCResultRegL), self._read_reg(self.CRCResultRegH)]

    def request(self):
        """Check if a tag is present. Returns (status, tag_type)."""
        self._write_reg(self.BitFramingReg, 0x07)
        data, _ = self._communicate(self.Transceive, [self.REQIDL])
        if data and len(data) == 2:
            return True, (data[0] << 8) | data[1]
        return False, 0

    def anticoll(self):
        """Get tag UID (4 bytes). Returns (status, uid_bytes)."""
        self._write_reg(self.BitFramingReg, 0x00)
        data, _ = self._communicate(self.Transceive, [self.ANTICOLL1, 0x20])
        if data and len(data) == 5:
            chk = 0
            for i in range(4):
                chk ^= data[i]
            if chk == data[4]:
                return True, data[:4]
        return False, []

    def select(self, uid):
        """Select a tag by UID."""
        buf = [self.SELECT1, 0x70] + uid
        chk = 0
        for b in uid:
            chk ^= b
        buf.append(chk)
        buf += self._crc(buf)
        data, _ = self._communicate(self.Transceive, buf)
        return data is not None and len(data) > 0

    def read_page(self, page):
        """Read 4 bytes from a page on NTAG213."""
        buf = [self.READ, page]
        buf += self._crc(buf)
        data, _ = self._communicate(self.Transceive, buf)
        if data and len(data) >= 4:
            return data[:4]
        return None

    def write_page(self, page, data4):
        """Write 4 bytes to a page on NTAG213."""
        buf = [self.WRITE, page] + list(data4[:4])
        buf += self._crc(buf)
        result, _ = self._communicate(self.Transceive, buf)
        return result is not None

    def read_spool_id(self):
        """Read spool ID from NTAG213 user page 4. Returns int or None."""
        ok, _ = self.request()
        if not ok:
            return None
        ok, uid = self.anticoll()
        if not ok:
            return None
        self.select(uid)
        page = self.read_page(4)  # NTAG213 user data starts at page 4
        if page:
            return (page[0] << 24) | (page[1] << 16) | (page[2] << 8) | page[3]
        return None

    def write_spool_id(self, spool_id):
        """Write spool ID to NTAG213 user page 4. Returns True on success."""
        ok, _ = self.request()
        if not ok:
            return False
        ok, uid = self.anticoll()
        if not ok:
            return False
        self.select(uid)
        data = [
            (spool_id >> 24) & 0xFF,
            (spool_id >> 16) & 0xFF,
            (spool_id >> 8) & 0xFF,
            spool_id & 0xFF,
        ]
        return self.write_page(4, data)
