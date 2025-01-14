import pygame
import random
import time
from pygame.locals import *
import mysql.connector
import bcrypt

# ============== PHẦN ĐĂNG KÝ / ĐĂNG NHẬP (nếu cần) ==============
def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',         # Tên người dùng MySQL của bạn
        password='uit12345', # Mật khẩu MySQL của bạn
        database='flappy_bird'
    )
    return conn

def register_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return "username already exists!"
    else:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()
        return "Register successful!"

def login_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
        return True
    else:
        return False

# ============== PHẦN GAME FLAPPY BIRD ==============
pygame.mixer.init()

# VARIABLES
SCREEN_WIDHT = 400
SCREEN_HEIGHT = 600 
SPEED = 10
GRAVITY = 1
GAME_SPEED = 15

GROUND_WIDHT = 2 * SCREEN_WIDHT
GROUND_HEIGHT = 100

PIPE_WIDHT = 80
PIPE_HEIGHT = 500

PIPE_GAP = 150

wing = 'assets/audio/wing.wav'
hit = 'assets/audio/hit.wav'

class Bird(pygame.sprite.Sprite):

    def __init__(self):
        pygame.sprite.Sprite.__init__(self)

        self.images = [
            pygame.image.load('assets/sprites/bluebird-upflap.png').convert_alpha(),
            pygame.image.load('assets/sprites/bluebird-midflap.png').convert_alpha(),
            pygame.image.load('assets/sprites/bluebird-downflap.png').convert_alpha()
        ]
        self.pro_image = pygame.image.load('assets/sprites/bluebird-pro.png').convert_alpha()

        self.speed = SPEED
        self.current_image = 0
        self.image = pygame.image.load('assets/sprites/bluebird-upflap.png').convert_alpha()
        self.mask = pygame.mask.from_surface(self.image)

        self.rect = self.image.get_rect()
        self.rect[0] = SCREEN_WIDHT / 6
        self.rect[1] = SCREEN_HEIGHT / 2

        # ----- Đếm số cột ống đã vượt qua kể từ lúc "nâng cấp"
        self.upgraded_pipes = 0  
        self.is_upgraded = False  # trạng thái chim đang ở "pro" hay không

    def update(self):
        self.current_image = (self.current_image + 1) % 3

        # Nếu chim đang "thường" -> hiển thị ảnh thường
        if not self.is_upgraded:
            self.image = self.images[self.current_image]

        # Tính physics rơi xuống
        self.speed += GRAVITY
        self.rect[1] += self.speed

    def bump(self):
        self.speed = -SPEED

    def begin(self):
        self.current_image = (self.current_image + 1) % 3
        self.image = self.images[self.current_image]

    def upgrade(self):
        """Cho chim sang dạng 'pro' và reset biến đếm ống đã vượt"""
        self.image = self.pro_image
        self.is_upgraded = True
        self.upgraded_pipes = 0

    def downgrade(self):
        """Quay về chim bình thường"""
        self.image = self.images[0]
        self.is_upgraded = False

    def eat_worm(self):
        """Khi chim ăn vật phẩm sâu, sẽ chuyển sang pro ngay."""
        self.upgrade()

class Pipe(pygame.sprite.Sprite):

    def __init__(self, inverted, xpos, ysize):
        pygame.sprite.Sprite.__init__(self)

        self.image = pygame.image.load('assets/sprites/pipe-red.png').convert_alpha()
        self.image = pygame.transform.scale(self.image, (PIPE_WIDHT, PIPE_HEIGHT))

        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        self.inverted = inverted

        # Đánh dấu ống đã được chim vượt qua chưa (để + điểm 1 lần)
        self.passed = False

        if inverted:
            # Ống trên
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect[1] = -(self.rect[3] - ysize)
        else:
            # Ống dưới
            self.rect[1] = SCREEN_HEIGHT - ysize

        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        global score
        self.rect[0] -= GAME_SPEED

        # Khi chim vượt qua ống dưới => +1 điểm
        # và ống này chưa được "passed" => + điểm 1 lần duy nhất
        if (not self.inverted) and (not self.passed) and (self.rect.right < bird.rect.left):
            self.passed = True
            score += 1

            # Nếu chim đang "pro" -> tăng số cột ống đã vượt
            if bird.is_upgraded:
                bird.upgraded_pipes += 1
                # Nếu đã vượt qua 3 cột kể từ lúc pro => downgrade
                if bird.upgraded_pipes >= 3:
                    bird.downgrade()

class Ground(pygame.sprite.Sprite):
    def __init__(self, xpos):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load('assets/sprites/base.png').convert_alpha()
        self.image = pygame.transform.scale(self.image, (GROUND_WIDHT, GROUND_HEIGHT))
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        self.rect[1] = SCREEN_HEIGHT - GROUND_HEIGHT

    def update(self):
        self.rect[0] -= GAME_SPEED

class Worm(pygame.sprite.Sprite):
    def __init__(self, xpos, ypos):
        pygame.sprite.Sprite.__init__(self)
        try:
            self.image = pygame.image.load('assets/sprites/worm.png').convert_alpha()
        except pygame.error as e:
            print(f"Không thể tải ảnh sâu: {e}")
            self.image = pygame.Surface((30, 30))
            self.image.fill((255, 0, 0))  # Nếu lỗi load, dùng ô vuông đỏ
        self.image = pygame.transform.scale(self.image, (30, 30))

        self.rect = self.image.get_rect()
        self.rect.center = (xpos, ypos)

    def update(self):
        self.rect[0] -= GAME_SPEED

def is_off_screen(sprite):
    return sprite.rect[0] < -(sprite.rect[2])

def get_random_pipes(xpos):
    size = random.randint(100, 300)
    pipe = Pipe(False, xpos, size)
    pipe_inverted = Pipe(True, xpos, SCREEN_HEIGHT - size - PIPE_GAP)
    return pipe, pipe_inverted

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDHT, SCREEN_HEIGHT))
pygame.display.set_caption('Flappy Bird')

BACKGROUND = pygame.image.load('assets/sprites/background-day.png')
BACKGROUND = pygame.transform.scale(BACKGROUND, (SCREEN_WIDHT, SCREEN_HEIGHT))

bird_group = pygame.sprite.Group()
bird = Bird()
bird_group.add(bird)

ground_group = pygame.sprite.Group()
for i in range(2):
    ground = Ground(GROUND_WIDHT * i)
    ground_group.add(ground)

pipe_group = pygame.sprite.Group()
for i in range(2):
    pipes = get_random_pipes(SCREEN_WIDHT * i + 800)
    pipe_group.add(pipes[0])
    pipe_group.add(pipes[1])

# Màu sắc
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Điểm số
score = 0

# Biến “xuyên cột” (chỉ 1 lần sau khi ăn sâu)
can_penetrate = False

# Nhóm sâu (vật phẩm)
worm_group = pygame.sprite.Group()

def create_worm_between_pipes(pipe_top, pipe_bottom):
    """Tạo sâu ở khoảng giữa 2 ống."""
    xpos = pipe_top.rect.centerx
    ypos = (pipe_top.rect.bottom + pipe_bottom.rect.top) // 2
    worm = Worm(xpos, ypos)
    worm_group.add(worm)

def update_worms():
    """Kiểm tra và xử lý logic ăn sâu."""
    global can_penetrate, score
    worm_group.update()

    # Xoá sâu nếu ra khỏi màn hình
    for worm in worm_group.sprites():
        if worm.rect.right < 0:
            worm_group.remove(worm)

    # Nếu chim chạm bất kỳ sâu nào => ăn sâu
    if pygame.sprite.spritecollideany(bird, worm_group):
        can_penetrate = True  # bật cờ xuyên cột (1 lần)
        for worm in worm_group.sprites():
            if bird.rect.colliderect(worm.rect):
                worm_group.remove(worm)
                bird.eat_worm()   # chim sang "pro"
                score += 1        # +1 điểm khi ăn sâu

def check_collision():
    """Kiểm tra va chạm và cho phép xuyên 1 lần nếu can_penetrate == True."""
    global can_penetrate

    # 1) va chạm ground => game over
    if pygame.sprite.groupcollide(bird_group, ground_group, False, False, pygame.sprite.collide_mask):
        return True

    # 2) Kiểm tra va chạm cột
    if pygame.sprite.groupcollide(bird_group, pipe_group, False, False, pygame.sprite.collide_mask):
        # Nếu đang có trạng thái xuyên => bỏ qua va chạm 1 lần
        if can_penetrate:
            can_penetrate = False  # dùng xong thì tắt
            return False
        else:
            return True

    return False

# VÒNG LẶP CHÍNH
clock = pygame.time.Clock()
while True:
    clock.tick(15)

    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            exit()
        if event.type == KEYDOWN:
            if event.key == K_SPACE or event.key == K_UP:
                bird.bump()
                pygame.mixer.music.load(wing)
                pygame.mixer.music.play()

    screen.blit(BACKGROUND, (0, 0))

    # Cập nhật, tịnh tiến ground
    if is_off_screen(ground_group.sprites()[0]):
        ground_group.remove(ground_group.sprites()[0])
        new_ground = Ground(GROUND_WIDHT - 20)
        ground_group.add(new_ground)

    # Cập nhật, tịnh tiến pipe
    if is_off_screen(pipe_group.sprites()[0]):
        pipe_group.remove(pipe_group.sprites()[0])
        pipe_group.remove(pipe_group.sprites()[0])

        pipes = get_random_pipes(SCREEN_WIDHT * 2)
        pipe_group.add(pipes[0])
        pipe_group.add(pipes[1])

        # Thả sâu giữa 2 ống mới
        create_worm_between_pipes(pipes[0], pipes[1])

    # Update chuyển động chim, ground, pipe, worm
    bird_group.update()
    ground_group.update()
    pipe_group.update()
    update_worms()  # ăn sâu trước khi check_collision

    # Kiểm tra va chạm
    if check_collision():
        pygame.mixer.music.load(hit)
        pygame.mixer.music.play()
        time.sleep(1)

        # Hiển thị GAME OVER
        font = pygame.font.Font(None, 72)
        game_over_text = font.render("GAME OVER", True, (255, 0, 0))
        screen.blit(game_over_text, 
                    (SCREEN_WIDHT // 2 - game_over_text.get_width() // 2, 
                     SCREEN_HEIGHT // 2 - game_over_text.get_height() // 2))
        pygame.display.update()
        time.sleep(3)
        break

    # Hiển thị điểm số
    font = pygame.font.Font(None, 36)
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (10, 10))

    # Vẽ các sprite
    bird_group.draw(screen)
    pipe_group.draw(screen)
    ground_group.draw(screen)
    worm_group.draw(screen)

    pygame.display.update()
