import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from drivers.ws2812 import WS2812
from enum import Enum



class Row(Enum):
    A = 1
    B = 2
    C = 3
    D = 4
    E = 5
    F = 6
    G = 7
    H = 8

class Row24(Enum):
    A = 1
    B = 2
    C = 3
    D = 4

class Row12(Enum):
    A=1; B=2; C=3

class Row6(Enum):
    A=1; B=2



# 行分块（重叠）
ROW_BLOCKS_24 = [(0,1), (2,3), (4,5), (6,7)]          # A–C, C–E, E–G, F–H
# 列分块（重叠）
COL_BLOCKS_24 = [(0,1), (2,3), (4,5), (6,7), (8,9), (10,11)]  # 6列平滑重叠

# 96孔 -> 8行×12列
# 12孔映射方案：
# 行分块: A→[0~2], B→[2~5], C→[5~7] （重叠两条边界）
# 列分块: 你可以选 (3,3,3,3) 或 (3,4,3,4)，这里举例 (3,3,3,3)
ROW_BLOCKS_12 = [(0,2), (2,5), (5,7)]
COL_BLOCKS_12 = [(0,2), (3,5), (6,8), (9,11)]  # 对应 1~3, 4~6, 7~9, 10~12

# 6孔板
# 行分块和列分块
ROW_BLOCKS_6 = [(0,4), (3,7)]      # A–E, D–H
COL_BLOCKS_6 = [(0,4), (3,8), (7,11)]  # 1–5, 5–9, 8–12


# 5x7 大写字母字模（A-Z），1=点亮，0=熄灭
FONT_5x7 = {
    "A": [
        [0,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    "B": [
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,0],
    ],
    "C": [
        [0,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,1],
        [0,1,1,1,0],
    ],
    "D": [
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,0],
    ],
    "E": [
        [1,1,1,1,1],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,1,1,1,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,1,1,1,1],
    ],
    "F": [
        [1,1,1,1,1],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,1,1,1,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
    ],
    "G": [
        [0,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,0],
        [1,0,1,1,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [0,1,1,1,0],
    ],
    "H": [
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    "I": [
        [1,1,1,1,1],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [1,1,1,1,1],
    ],
    "J": [
        [0,0,1,1,1],
        [0,0,0,1,0],
        [0,0,0,1,0],
        [0,0,0,1,0],
        [1,0,0,1,0],
        [1,0,0,1,0],
        [0,1,1,0,0],
    ],
    "K": [
        [1,0,0,0,1],
        [1,0,0,1,0],
        [1,0,1,0,0],
        [1,1,0,0,0],
        [1,0,1,0,0],
        [1,0,0,1,0],
        [1,0,0,0,1],
    ],
    "L": [
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,1,1,1,1],
    ],
    "M": [
        [1,0,0,0,1],
        [1,1,0,1,1],
        [1,0,1,0,1],
        [1,0,1,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    "N": [
        [1,0,0,0,1],
        [1,1,0,0,1],
        [1,0,1,0,1],
        [1,0,0,1,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    "O": [
        [0,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [0,1,1,1,0],
    ],
    "P": [
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
    ],
    "Q": [
        [0,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,1,0,1],
        [1,0,0,1,0],
        [0,1,1,0,1],
    ],
    "R": [
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,0],
        [1,0,1,0,0],
        [1,0,0,1,0],
        [1,0,0,0,1],
    ],
    "S": [
        [0,1,1,1,1],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [0,1,1,1,0],
        [0,0,0,0,1],
        [0,0,0,0,1],
        [1,1,1,1,0],
    ],
    "T": [
        [1,1,1,1,1],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
    ],
    "U": [
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [0,1,1,1,0],
    ],
    "V": [
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [0,1,0,1,0],
        [0,1,0,1,0],
        [0,0,1,0,0],
    ],
    "W": [
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,1,0,1],
        [1,0,1,0,1],
        [1,0,1,0,1],
        [1,1,0,1,1],
        [1,0,0,0,1],
    ],
    "X": [
        [1,0,0,0,1],
        [0,1,0,1,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,1,0,1,0],
        [1,0,0,0,1],
    ],
    "Y": [
        [1,0,0,0,1],
        [0,1,0,1,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
    ],
    "Z": [
        [1,1,1,1,1],
        [0,0,0,0,1],
        [0,0,0,1,0],
        [0,0,1,0,0],
        [0,1,0,0,0],
        [1,0,0,0,0],
        [1,1,1,1,1],
    ],
}


class Light:
    def __init__(self,color_correction=(255, 200, 150),global_brightness:int = 200) -> None:
        # 灯板对象
        self.led_panel = WS2812()
        # 初始化参数
        self.color_correction = color_correction
        self.global_brightness = global_brightness
        self.update_config()

        # 百分比
        self.pencent = 0

        self.letter = ''


    def update_config(self):
        # 设置颜色矫正
        self.led_panel.set_color_correction(*self.color_correction)
        # 设置全局亮度
        self.led_panel.set_global_brightness(200)

    # 按顺序的序号点亮
    def _sigle(self,n,r=255,g=255,b=255,brightness=50):
        self.led_panel.set_pixel_color(n, r, g, b, brightness)
        self.led_panel.show()

    # 按96孔点亮（12x8，横向）
    def well_96(self,row:Row|str,line:int,r=255,g=255,b=255,brightness=50):
        # --- 参数规范化 ---
        if isinstance(row, str):
            row = row.strip().upper()
            if row not in Row.__members__:
                raise ValueError(f"row 必须是 A..H 或 Row 枚举，收到: {row}")
            row = Row[row]
        elif not isinstance(row, Row):
            raise TypeError("row 必须是 Row 枚举或 'A'..'H'")

        if not (1 <= line <= 12):
            raise ValueError(f"line(列号)必须在 1..12，收到: {line}")
        
        # 亮度范围简单裁剪到 0..100（若你的底层用 0..255 可自行换算）
        brightness = max(0, min(100, int(brightness)))

        # -------- 计算像素索引（从左到右） --------
        row_idx = row.value - 1    # A→0, B→1, ..., H→7
        col_idx = 12-line         # 1→0, 12→11
        n = row_idx * 12 + col_idx  # 横向编号，共 96 点（0~95）

        self.led_panel.clear()
        self._sigle(n, r, g, b, brightness)
        return n
    
    # 按24孔点亮
    def well_24(self, row24: Row24 | str, col24: int,
                         r=255, g=255, b=255, brightness=50):
        """
        在96孔(8x12)平面上点亮24孔(4x6)的对应区块（可重叠映射）。
        """
        # 参数规范化
        if isinstance(row24, str):
            row24 = Row24[row24.strip().upper()]
        elif not isinstance(row24, Row24):
            raise TypeError("row24 必须是 Row24 或 'A'..'D'")
        if not (1 <= col24 <= 6):
            raise ValueError("24孔列必须是 1..6")

        row_range = ROW_BLOCKS_24[row24.value - 1]
        col_range = COL_BLOCKS_24[6-col24]

        lit = []
        self.led_panel.clear()
        for rr in range(row_range[0], row_range[1] + 1):
            for cc in range(col_range[0], col_range[1] + 1):
                n = rr * 12 + cc
                self._sigle(n, r, g, b, brightness)
                lit.append(n)
        return lit

    # 按12孔点亮
    def well_12(self, row12: Row12 | str, col12: int,
                         r=255, g=255, b=255, brightness=50):
        """
        在96孔(8x12)平面上点亮12孔(3x4)的对应区块。
        行映射采用3/4/3可重叠；列映射3/3/3/3或自定义。
        """
        if isinstance(row12, str):
            row12 = Row12[row12.strip().upper()]
        elif not isinstance(row12, Row12):
            raise TypeError("row12 必须是 Row12 或 'A'..'C'")
        if not (1 <= col12 <= 4):
            raise ValueError("12孔列必须是 1..4")

        row_range = ROW_BLOCKS_12[row12.value-1]
        col_range = COL_BLOCKS_12[4-col12]

        lit = []
        self.led_panel.clear()
        for rr in range(row_range[0], row_range[1]+1):
            for cc in range(col_range[0], col_range[1]+1):
                n = rr * 12 + cc
                self._sigle(n, r, g, b, brightness)
                lit.append(n)
        return lit

    # 按6孔点亮
    def well_6(self, row6: Row6 | str, col6: int,
                        r=255, g=255, b=255, brightness=50):
        """
        在96孔(8x12)平面上点亮6孔(2x3)的对应大区块。
        行映射采用(0~4)/(3~7)，列映射(0~4)/(4~8)/(8~11)。
        """
        # 参数规范化
        if isinstance(row6, str):
            row6 = Row6[row6.strip().upper()]
        elif not isinstance(row6, Row6):
            raise TypeError("row6 必须是 Row6 或 'A'..'B'")
        if not (1 <= col6 <= 3):
            raise ValueError("6孔列必须是 1..3")

        row_range = ROW_BLOCKS_6[row6.value - 1]
        col_range = COL_BLOCKS_6[3-col6]

        lit = []
        self.led_panel.clear()
        for rr in range(row_range[0], row_range[1] + 1):
            for cc in range(col_range[0], col_range[1] + 1):
                n = rr * 12 + cc
                self._sigle(n, r, g, b, brightness)
                lit.append(n)
        return lit

    # 全部点亮
    def all(self,r=255,g=255,b=255,brightness=50):
        for i in range(96):
            self._sigle(i,r,g,b,brightness)

    # 全部关闭
    def close(self):
        self.led_panel.clear()

    # 跑马灯
    def rainbow(self):
        self.led_panel.rainbow_cycle()


    # 显示字母
    def _render_char_5x7(self, ch: str, row0: int, col0: int, r=255, g=255, b=255, brightness=10):
        """
        在 (row0, col0) 放置一个 5x7 字符（左上角坐标，0基），超界自动忽略。
        """
        ch = (ch or " ").upper()
        if ch not in FONT_5x7:
            return  # 非 A-Z 直接忽略（也可做空格）
        pat = FONT_5x7[ch]
        for y in range(7):
            for x in range(5):
                if pat[y][x]:
                    rr = row0 + y
                    cc = col0 + x
                    if 0 <= rr < 8 and 0 <= cc < 12:
                        n = rr * 12 + cc
                        self._sigle(n, r, g, b, brightness)

    def display(self, letters,
                            r=0, g=255, b=0, brightness=10,
                            top: int = 0, gap_cols: int = 2):
        """
        在 96 孔（8x12）灯板上显示任意两个字母（A-Z）。
        - left/right: 单个字符（取其第一个字符）
        - 版面：左5列 + gap_cols + 右5列，默认 gap=2，正好占满 12 列
        - top: 顶部起始行（0~1 比较合适；字模高7行）
        """
        left = (letters[0] or " ")[0].upper()
        right = (letters[1] or " ")[0].upper()

        # 计算左右起始列
        left_col = 0
        right_col = 5 + gap_cols  # 默认 5+2=7 -> 右字从第7列开始

        self.led_panel.clear()
        
        self._render_char_5x7(left,  top, left_col,  r, g, b, brightness)
        self._render_char_5x7(right, top, right_col, r, g, b, brightness)


    def progress_last_row(self, percent: float,
                      fill_color=(100, 100, 0),      # 进度填充颜色
                      bg_color=(30, 30, 30),       # 背景颜色（未填充）
                      max_brightness=20,           # 填充段亮度 0..100
                      bg_brightness=10,            # 背景段亮度 0..100
                      origin: str = "left"):       # "left" 从左到右；"right" 从右到左
        """
        在最后一行(第8行)显示进度条。96孔 = 8行×12列，索引 n = row*12 + col（非蛇形）
        - percent: 0..100
        - origin: "left" / "right"（进度方向）
        - 有“半格”过渡：当前边界格按比例降低亮度，增强平滑感
        """
        # 规格化
        p = max(0.0, min(100.0, float(percent)))
        rr = 7  # 最后一行，0基索引
        total_cols = 12
        # 进度映射到 0..12 列
        prog_cols_float = p / 100.0 * total_cols
        full_cols = int(prog_cols_float)                # 完整填充的格数
        frac = prog_cols_float - full_cols              # 边界格的比例 (0..1)

        # 渲染每一列
        for i in range(total_cols):
            # 计算当前列的真实列索引（支持从右向左）
            col = i if origin == "left" else (total_cols - 1 - i)
            n = rr * 12 + col

            if i < full_cols:
                # 完整填充列
                r, g, b = fill_color
                self._sigle(n, r, g, b, max_brightness)
            elif i == full_cols and frac > 0 and full_cols < total_cols:
                # 半格：按比例亮度（至少给点亮度，避免太暗看不见）
                r, g, b = fill_color
                partial_brightness = max(5, int(max_brightness * frac))
                self._sigle(n, r, g, b, partial_brightness)
            else:
                # 背景
                r, g, b = bg_color
                self._sigle(n, r, g, b, bg_brightness)

    def show_pencent(self,show=True):
        if show:
            self.progress_last_row(self.pencent,)

    def update_percent(self,percent):
        self.pencent = percent
        self.show_pencent()



if __name__ == '__main__':
    import time

    light = Light()

    light.display('ld')


    for i in range(100):
        light.update_percent(i)
        time.sleep(0.01)

    # time.sleep(1000)
    light.display('OK')

    # time.sleep(5)

    # light.rainbow()

    # while True:
    #     time.sleep(1)