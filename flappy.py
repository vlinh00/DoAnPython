import pygame, random, time
from pygame.locals import *
import mysql.connector
import bcrypt

# Thiết lập kết nối với MySQL
def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',  # Sửa tên người dùng MySQL của bạn
        password='',  # Sửa mật khẩu MySQL của bạn
        database='flappy_bird'
    )
    return conn

# Hàm đăng ký người dùng
def register_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        return "username already exists!"
    else:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()
        return "Register succecsful!"
    

# Kiểm tra mật khẩu đã mã hóa khi đăng nhập
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

#VARIABLES
SCREEN_WIDHT = 400
SCREEN_HEIGHT = 600
SPEED = 10
GRAVITY = 5
GAME_SPEED = 15

GROUND_WIDHT = 2 * SCREEN_WIDHT
GROUND_HEIGHT= 100

PIPE_WIDHT = 80
PIPE_HEIGHT = 500

PIPE_GAP = 150

wing = 'assets/audio/wing.wav'
hit = 'assets/audio/hit.wav'

pygame.mixer.init()


class Bird(pygame.sprite.Sprite):

    def __init__(self):
        pygame.sprite.Sprite.__init__(self)

        self.images =  [pygame.image.load('assets/sprites/bluebird-upflap.png').convert_alpha(),
                        pygame.image.load('assets/sprites/bluebird-midflap.png').convert_alpha(),
                        pygame.image.load('assets/sprites/bluebird-downflap.png').convert_alpha()]

        self.speed = SPEED

        self.current_image = 0
        self.image = pygame.image.load('assets/sprites/bluebird-upflap.png').convert_alpha()
        self.mask = pygame.mask.from_surface(self.image)

        self.rect = self.image.get_rect()
        self.rect[0] = SCREEN_WIDHT / 6
        self.rect[1] = SCREEN_HEIGHT / 2

    def update(self):
        self.current_image = (self.current_image + 1) % 3
        self.image = self.images[self.current_image]
        self.speed += GRAVITY

        #UPDATE HEIGHT
        self.rect[1] += self.speed

    def bump(self):
        self.speed = -SPEED

    def begin(self):
        self.current_image = (self.current_image + 1) % 3
        self.image = self.images[self.current_image]




class Pipe(pygame.sprite.Sprite):

    def __init__(self, inverted, xpos, ysize):
        pygame.sprite.Sprite.__init__(self)

        self. image = pygame.image.load('assets/sprites/pipe-green.png').convert_alpha()
        self.image = pygame.transform.scale(self.image, (PIPE_WIDHT, PIPE_HEIGHT))


        self.rect = self.image.get_rect()
        self.rect[0] = xpos

        if inverted:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect[1] = - (self.rect[3] - ysize)
        else:
            self.rect[1] = SCREEN_HEIGHT - ysize


        self.mask = pygame.mask.from_surface(self.image)


    def update(self):
        self.rect[0] -= GAME_SPEED

        

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
BEGIN_IMAGE = pygame.image.load('assets/sprites/message.png').convert_alpha()

bird_group = pygame.sprite.Group()
bird = Bird()
bird_group.add(bird)

ground_group = pygame.sprite.Group()

for i in range (2):
    ground = Ground(GROUND_WIDHT * i)
    ground_group.add(ground)

pipe_group = pygame.sprite.Group()
for i in range (2):
    pipes = get_random_pipes(SCREEN_WIDHT * i + 800)
    pipe_group.add(pipes[0])
    pipe_group.add(pipes[1])

# Màu sắc
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)

# Vị trí và kích thước ô nhập
username_rect = pygame.Rect(100, 175, 200, 40)
password_rect = pygame.Rect(100, 260, 200, 40)

# Biến lưu giá trị nhập
username_text = ''
password_text = ''
active_input = None  # Biến kiểm tra ô nhập nào đang được chọn

# Font chữ
font = pygame.font.Font(None, 30)

# Đăng ký, đăng nhập
def draw_text(surface, text, size, x, y, color):
    font = pygame.font.Font(None, size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    text_rect.center = (x, y)
    surface.blit(text_surface, text_rect)


def login_or_register_screen():
    input_active = {'username': False, 'password': False}
    input_text = {'username': '', 'password': ''}
    action = None  # None, "login", "register"
    message = ""

    screen.fill((0, 0, 0))  # Black background

    while True:
        screen.blit(BACKGROUND, (0, 0))
        # screen.fill(GRAVITY)  # Nền trắng
        # Vẽ các text và ô nhập
        draw_text(screen, "Flappy Bird", 50, SCREEN_WIDHT // 2, 50, BLACK)
        draw_text(screen, "Username:", 30, SCREEN_WIDHT // 2, 150, BLACK)
        pygame.draw.rect(screen, BLUE if input_active['username'] else GRAY, username_rect, 2)
        draw_text(screen, input_text['username'], 30, username_rect.x + 100, username_rect.y + 20, BLACK)

        draw_text(screen, "Password:", 30, SCREEN_WIDHT // 2, 240, BLACK)
        pygame.draw.rect(screen, BLUE if input_active['password'] else GRAY, password_rect, 2)
        draw_text(screen, '*' * len(input_text['password']), 30, password_rect.x + 100, password_rect.y + 20, BLACK)

        # Vẽ nút
        pygame.draw.rect(screen, (0, 128, 255), (100, 350, 100, 40))  # Register button
        draw_text(screen, "Register", 25, 150, 370, WHITE)
        pygame.draw.rect(screen, (0, 128, 255), (220, 350, 100, 40))  # Login button
        draw_text(screen, "Login", 25, 270, 370, WHITE)

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                return None

            if event.type == MOUSEBUTTONDOWN:
                # Handle clicks on buttons
                if 100 <= event.pos[0] <= 200 and 350 <= event.pos[1] <= 390:
                    action = "register"
                elif 220 <= event.pos[0] <= 320 and 350 <= event.pos[1] <= 390:
                    action = "login"

                # Check if clicking in text input areas
                if 100 <= event.pos[0] <= 300 and 175 <= event.pos[1] <= 225:  # Username area
                    input_active['username'] = True
                    input_active['password'] = False
                elif 100 <= event.pos[0] <= 300 and 275 <= event.pos[1] <= 325:  # Password area
                    input_active['username'] = False
                    input_active['password'] = True

            if event.type == KEYDOWN:
                if input_active['username']:
                    if event.key == K_BACKSPACE:
                        input_text['username'] = input_text['username'][:-1]
                    else:
                        input_text['username'] += event.unicode
                elif input_active['password']:
                    if event.key == K_BACKSPACE:
                        input_text['password'] = input_text['password'][:-1]
                    else:
                        input_text['password'] += event.unicode

        # Process login or register action
        if action:
            username = input_text['username']
            password = input_text['password']

            if action == "register":
                if username and password:
                    message = register_user(username, password)  # Gọi hàm insert vào DB
                else:
                    message = "Username and password cannot be empty!"
                action = None  # Reset action to avoid repeated insertions

            elif action == "login":
                if username and password:
                    if login_user(username, password):  # Gọi hàm kiểm tra đăng nhập
                        return True
                    else:
                        message = "Invalid username or password!"
                else:
                    message = "Username and password cannot be empty!"
                action = None  # Reset action to avoid repeated checks

        # Display message if any
        if message:
            draw_text(screen, message, 30, SCREEN_WIDHT // 2, 420, (255, 0, 0))

        pygame.display.update()


# Chạy giao diện đăng nhập/đăng ký trước khi vào game
if login_or_register_screen():
    print("Game starts...")
    clock = pygame.time.Clock()

    begin = True

    while begin:

        clock.tick(15)

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
            if event.type == KEYDOWN:
                if event.key == K_SPACE or event.key == K_UP:
                    bird.bump()
                    pygame.mixer.music.load(wing)
                    pygame.mixer.music.play()
                    begin = False

        screen.blit(BACKGROUND, (0, 0))
        screen.blit(BEGIN_IMAGE, (120, 150))

        if is_off_screen(ground_group.sprites()[0]):
            ground_group.remove(ground_group.sprites()[0])

            new_ground = Ground(GROUND_WIDHT - 20)
            ground_group.add(new_ground)

        bird.begin()
        ground_group.update()

        bird_group.draw(screen)
        ground_group.draw(screen)

        pygame.display.update()


    while True:

        clock.tick(15)

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
            if event.type == KEYDOWN:
                if event.key == K_SPACE or event.key == K_UP:
                    bird.bump()
                    pygame.mixer.music.load(wing)
                    pygame.mixer.music.play()

        screen.blit(BACKGROUND, (0, 0))

        if is_off_screen(ground_group.sprites()[0]):
            ground_group.remove(ground_group.sprites()[0])

            new_ground = Ground(GROUND_WIDHT - 20)
            ground_group.add(new_ground)

        if is_off_screen(pipe_group.sprites()[0]):
            pipe_group.remove(pipe_group.sprites()[0])
            pipe_group.remove(pipe_group.sprites()[0])

            pipes = get_random_pipes(SCREEN_WIDHT * 2)

            pipe_group.add(pipes[0])
            pipe_group.add(pipes[1])

        bird_group.update()
        ground_group.update()
        pipe_group.update()

        bird_group.draw(screen)
        pipe_group.draw(screen)
        ground_group.draw(screen)

        pygame.display.update()

        if (pygame.sprite.groupcollide(bird_group, ground_group, False, False, pygame.sprite.collide_mask) or
                pygame.sprite.groupcollide(bird_group, pipe_group, False, False, pygame.sprite.collide_mask)):
            pygame.mixer.music.load(hit)
            pygame.mixer.music.play()
            time.sleep(1)
            break

