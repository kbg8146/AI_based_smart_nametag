from PIL import Image, ImageDraw

# 1. 지도 불러오기
img = Image.open("your_map.png").convert("L")  # 'L' = grayscale 흑백

# 2. 현재 위치 좌표 찍기 (예: (320, 240))
draw = ImageDraw.Draw(img)
x, y = 320, 240  # 현재 위치 (픽셀 기준)
r = 6  # 원 반지름
draw.ellipse((x - r, y - r, x + r, y + r), fill=0)  # 검은 원

# 3. BMP 저장 (8-bit grayscale BMP)
img.save("map.bmp", format="BMP")
