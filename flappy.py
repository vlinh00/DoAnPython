import pygame, random, time
from pygame.locals import *
import mysql.connector
import bcrypt
import random

# ============== PHẦN ĐĂNG KÝ / ĐĂNG NHẬP (nếu cần) ==============
# Thiết lập kết nối với MySQL
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='flappy_bird'
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# Hàm đăng ký người dùng
def register_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        return "username already exists!"
    else:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        highscore = 0
        level = 1
        cursor.execute("INSERT INTO users (username, password, highscore, level) VALUES (%s, %s, %s, %s)", (username, hashed_password, highscore, level))
        conn.commit()
        cursor.close()
        conn.close()
        return "Register successful!"
    

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

# ============== PHẦN GAME FLAPPY BIRD ==============
#VARIABLES
SCREEN_WIDHT = 400
SCREEN_HEIGHT = 600
SPEED = 15
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

        self.pro_image = pygame.image.load('assets/sprites/bluebird-pro.png').convert_alpha()

        self.speed = SPEED

        self.current_image = 0
        self.image = pygame.image.load('assets/sprites/bluebird-upflap.png').convert_alpha()
        self.mask = pygame.mask.from_surface(self.image)

        self.rect = self.image.get_rect()
        self.rect[0] = SCREEN_WIDHT / 6
        self.rect[1] = SCREEN_HEIGHT / 2

        # Thêm thuộc tính mới để theo dõi trạng thái có đạn hay không
        self.has_bullets = False

        # ----- Đếm số cột ống đã vượt qua kể từ lúc "nâng cấp"
        self.upgraded_pipes = 0  
        self.is_upgraded = False  # trạng thái chim đang ở "pro" hay không

    def update(self):
        self.current_image = (self.current_image + 1) % 3

        # Nếu chim đang "thường" -> hiển thị ảnh thường
        if not self.is_upgraded:
            self.image = self.images[self.current_image]

        # self.image = self.images[self.current_image]
        self.speed += GRAVITY
        #UPDATE HEIGHT
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

    # Phương thức mới để bật/tắt trạng thái có đạn
    def toggle_bullets(self, has_bullets):
        self.has_bullets = has_bullets

    # Bắn đạn
    def shoot_bullet(self):
        if self.has_bullets:
            bullet = Bullet(self.rect.x + self.rect.width, self.rect.centery)
            return bullet
        return None


# Ống
class Pipe(pygame.sprite.Sprite):

    def __init__(self, inverted, xpos, ysize):
        pygame.sprite.Sprite.__init__(self)

        self. image = pygame.image.load('assets/sprites/pipe-red.png').convert_alpha()
        self.image = pygame.transform.scale(self.image, (PIPE_WIDHT, PIPE_HEIGHT))


        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        
        self.inverted = inverted

        # Đánh dấu ống đã được chim vượt qua chưa (để + điểm 1 lần)
        self.passed = False

        if inverted:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect[1] = -(self.rect[3] - ysize)
        else:
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
                if bird.upgraded_pipes >= 2:
                    can_penetrate = False
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
       

def is_off_screen(sprite):
    return sprite.rect[0] < -(sprite.rect[2])
    # return sprite.rect.right < 0

def get_random_pipes(xpos):
    size = random.randint(100, 300)
    pipe = Pipe(False, xpos, size)
    pipe_inverted = Pipe(True, xpos, SCREEN_HEIGHT - size - PIPE_GAP)
    return pipe, pipe_inverted

# Sâu vật phẩm
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

# Vật phẩm đạn
class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.image.load('assets/sprites/bullet.png')  # Hình ảnh buff đạn
        self.image = pygame.transform.scale(self.image, (30, 30))  # Kích thước
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    def update(self):
        self.rect.x -= 3  # Di chuyển từ phải sang trái
        if self.rect.right < 0:  # Xóa vật phẩm khi ra khỏi màn hình
            self.kill() 

def spawn_powerup():
    if random.randint(1, 100) <= 10 and len(powerup_group) < 1:  # 15% cơ hội xuất hiện vật phẩm
        x = 800  # Xuất hiện ngoài màn hình
        y = random.randint(100, 400)  # Ngẫu nhiên trên đường bay
        print('tạo vật phẩm')
        powerup = PowerUp(x, y)
        powerup_group.add(powerup)



class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # self.image = pygame.Surface((10, 5))
        # self.image.fill((255, 0, 0))  # Màu đỏ
        self.image = pygame.image.load('assets/sprites/shutbullet.png')  # Hình ảnh buff đạn
        self.image = pygame.transform.scale(self.image, (30, 30))  # Kích thước 
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    def update(self):
        self.rect.x += 15  # Đạn bay sang phải
        if self.rect.left > 800:  # Xóa đạn khi ra khỏi màn hình
            self.kill()

# Màu sắc
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
CORAL = (255,127,80)

# Điểm số
score = 0

# Biến “xuyên cột” (chỉ 1 lần sau khi ăn sâu)
can_penetrate = False


def create_worm_between_pipes(pipe_top, pipe_bottom):
    """Tạo sâu ở khoảng giữa 2 ống."""
    if random.randint(1, 100) <= 10 and len(worm_group) < 2:  # 15% cơ hội xuất hiện vật phẩm
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
    # pygame.display.update()


# Vị trí và kích thước ô nhập
username_rect = pygame.Rect(100, 175, 200, 40)
password_rect = pygame.Rect(100, 260, 200, 40)

# Biến lưu giá trị nhập
username_text = ''
password_text = ''
active_input = None  # Biến kiểm tra ô nhập nào đang được chọn

# Font chữ
# font = pygame.font.Font(None, 30)

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
                        return username
                    else:
                        message = "Invalid username or password!"
                else:
                    message = "Username and password cannot be empty!"
                action = None  # Reset action to avoid repeated checks

        # Display message if any
        if message:
            draw_text(screen, message, 30, SCREEN_WIDHT // 2, 420, (255, 0, 0))

        pygame.display.update()

# Thêm một hàm để hiển thị màn hình cài đặt
def settings_screen(username):
    level = get_level(username)  # Giá trị mặc định của cấp độ
    high_score = get_high_score(username)  # Lấy điểm cao nhất từ cơ sở dữ liệu
    # high_score = 100
    while True:
        if level == 1:
            level_text = "Easy"
        elif level == 2:
            level_text = "Medium"
        else:
            level_text = "Hard"
        screen.blit(BACKGROUND, (0, 0))
        draw_text(screen, "Settings", 50, SCREEN_WIDHT // 2, 50, BLACK)
        
        # Hiển thị điểm cao nhất
        draw_text(screen, f"High Score: {high_score}", 30, SCREEN_WIDHT // 2, 150, BLACK)
        
        # Hiển thị cấp độ hiện tại
        draw_text(screen, f"Level: {level_text}", 30, SCREEN_WIDHT // 2, 250, BLACK )

        # Nút giảm cấp độ
        pygame.draw.rect(screen, BLUE, (100, 300, 50, 40))  # Nút "-"
        draw_text(screen, "-", 30, 125, 320, WHITE)

        # Nút tăng cấp độ
        pygame.draw.rect(screen, BLUE, (250, 300, 50, 40))  # Nút "+"
        draw_text(screen, "+", 30, 275, 320, WHITE)


        # Nút quay lại
        pygame.draw.rect(screen, (255, 0, 0), (150, 400, 100, 40))  # Nút "Back"
        draw_text(screen, "Back", 30, 200, 420, WHITE)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                return

            if event.type == MOUSEBUTTONDOWN:
                if 100 <= event.pos[0] <= 150 and 300 <= event.pos[1] <= 340:  # Giảmcấp độ
                    if level > 1:  # Giới hạn tối thiểu cấp độ
                        level -= 1
                elif 250 <= event.pos[0] <= 300 and 300 <= event.pos[1] <= 340:  # Tăng cấp độ
                    if level < 3:  # Giới hạn tối đa cấp độ
                        level += 1
                elif 150 <= event.pos[0] <= 250 and 400 <= event.pos[1] <= 440:  # Nút quay lại
                    pygame.time.delay(100)
                    return level

# Hàm để lấy điểm cao nhất từ cơ sở dữ liệu
def get_high_score(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT highscore FROM users WHERE username = %s",(username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result[0] else 0

# Hàm để lấy level từ CSDL
def get_level(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT level FROM users WHERE username = %s",(username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result[0] else 0

# Hàm để cập nhật level đến CSDL
def update_level(username, level):
    user_id = get_user_id(username)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET level = %s WHERE id = %s", (level, user_id))
    conn.commit()
    result = cursor.rowcount
    cursor.close()
    conn.close()
    return True if result > 0 else False

# Cập nhật điểm cao nhất
def update_highscore(username, highscore):
    user_id = get_user_id(username)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET highscore = %s WHERE id = %s", (highscore, user_id))
    conn.commit()
    result = cursor.rowcount
    cursor.close()
    conn.close()
    return True if result > 0 else False

# Lấy user_id
def get_user_id(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s",(username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result[0] else 0

# Hàm xử lý Game Over
def game_over_screen(score):
    global begin
    global start
    while True:
        screen.fill((0, 0, 0))  # Nền đen
        screen.blit(BACKGROUND, (0, 0))

        # Hiển thị thông báo Game Over
        draw_text(screen, "Game Over", 50, SCREEN_WIDHT // 2, SCREEN_HEIGHT // 2 - 100, (255, 0, 0))
        draw_text(screen, f"Score: {score}", 40, SCREEN_WIDHT // 2, SCREEN_HEIGHT // 2 - 50, (255, 255, 255))


        # Nút Settings
        pygame.draw.rect(screen, (128, 128, 128), (150, 15, 100, 30))
        draw_text(screen, "Settings", 28, 200, 30, WHITE)

        # Nút Logout
        pygame.draw.rect(screen, (255, 165, 0), (150, 60, 100, 30))  # Màu cam
        draw_text(screen, "Logout", 28, 200, 75, WHITE)

        # Nút Quit
        pygame.draw.rect(screen, (255, 0, 0), (150, 105, 100, 30))
        draw_text(screen, "Quit", 28, 200, 120, WHITE)     

        # Nút Play Again
        pygame.draw.rect(screen, (0, 128, 255), (118, 350, 180, 40))
        draw_text(screen, "Play Again", 30, 210, 370, WHITE)

        # Nút Exit
        # pygame.draw.rect(screen, (255, 0, 0), (100, 420, 200, 50))
        # draw_text(screen, "Exit", 30, 200, 445, WHITE)

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                return False

            if event.type == MOUSEBUTTONDOWN:
                if 118 <= event.pos[0] <= 298 and 350 <= event.pos[1] <= 390:  # Nút Play Again
                    return True
                elif 150 <= event.pos[0] <= 250 and 15 <= event.pos[1] <= 45: # Nút Settings
                    selected_level = settings_screen(user)
                    if selected_level:
                        update_level(user, selected_level)
                elif 150 <= event.pos[0] <= 250 and 60 <= event.pos[1] <= 90:  # Nút Logout
                    # begin = False
                    # start = False
                    return False
                elif 150 <= event.pos[0] <= 250 and 105 <= event.pos[1] <= 135:  # Nút Quit
                    pygame.quit()
                    return False
        pygame.display.update()

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDHT, SCREEN_HEIGHT))
pygame.display.set_caption('Flappy Bird')

BACKGROUND = pygame.image.load('assets/sprites/background-day.png')
BACKGROUND = pygame.transform.scale(BACKGROUND, (SCREEN_WIDHT, SCREEN_HEIGHT))
BEGIN_IMAGE = pygame.image.load('assets/sprites/message.png').convert_alpha()
GAMEOVER = pygame.image.load('assets/sprites/gameover.png')

bird_group = pygame.sprite.Group()
bird = Bird()
bird_group.add(bird)

worm_group = pygame.sprite.Group()
powerup_group = pygame.sprite.Group()
bullet_group = pygame.sprite.Group()
# Nhóm sâu (vật phẩm)
# worm_group = pygame.sprite.Group()

ground_group = pygame.sprite.Group()

for i in range (2):
    ground = Ground(GROUND_WIDHT * i)
    ground_group.add(ground)

pipe_group = pygame.sprite.Group()
for i in range (2):
    pipes = get_random_pipes(SCREEN_WIDHT * i + 800)
    pipe_group.add(pipes[0])
    pipe_group.add(pipes[1])


FPS = 15
fpsClock = pygame.time.Clock()
begin = True
start = False
selected_level = 1
# Chạy giao diện đăng nhập/đăng ký trước khi vào game
if __name__ == '__main__':
    while True:
        user = login_or_register_screen()
        if user:
            # bird = Bird()
            # bird_group.add(bird)

            # for i in range (2):
            #     pipes = get_random_pipes(SCREEN_WIDHT * i + 800)
            #     pipe_group.add(pipes[0])
            #     pipe_group.add(pipes[1])
            # Bắt đầu game
            num_bullet = 0
            begin = True
            start = False
            while begin:
                score = 0
                fpsClock.tick(FPS)


                for event in pygame.event.get():
                    if event.type == QUIT:
                        pygame.quit()
                    if event.type == KEYDOWN:
                        if event.key == K_SPACE or event.key == K_UP:
                            bird.bump()
                            pygame.mixer.music.load(wing)
                            pygame.mixer.music.play()
                            begin = False
                            start = True

                screen.blit(BACKGROUND, (0, 0))
                screen.blit(BEGIN_IMAGE, (120, 150))

                # Nút Settings
                pygame.draw.rect(screen, (128, 128, 128), (150, 15, 100, 30))
                draw_text(screen, "Settings", 28, 200, 30, WHITE)

                # Nút Logout
                pygame.draw.rect(screen, (255, 165, 0), (150, 60, 100, 30))  # Màu cam
                draw_text(screen, "Logout", 28, 200, 75, WHITE)

                # Nút Quit
                pygame.draw.rect(screen, (255, 0, 0), (150, 105, 100, 30))
                draw_text(screen, "Quit", 28, 200, 120, WHITE)
                
                # Nút Play
                pygame.draw.rect(screen, (0, 128, 255), (150, 210, 100, 30))
                draw_text(screen, "Play", 28, 200, 225, WHITE)

            
                pygame.display.flip()
                
                if event.type == MOUSEBUTTONDOWN:
                    if 150 <= event.pos[0] <= 250 and 210 <= event.pos[1] <= 240:  # Nút Play
                        bird.bump()
                        pygame.mixer.music.load(wing)
                        pygame.mixer.music.play()
                        begin = False
                        start = True
                    elif 150 <= event.pos[0] <= 250 and 15 <= event.pos[1] <= 45: # Nút Settings
                        selected_level = settings_screen(user)
                        if selected_level:
                            update_level(user, selected_level)
                        # selected_level = settings_screen()
                        # print(f"Selected Level: {selected_level}")
                    elif 150 <= event.pos[0] <= 250 and 60 <= event.pos[1] <= 90:  # Nút Logout
                        begin = False
                        start = False
                    elif 150 <= event.pos[0] <= 250 and 105 <= event.pos[1] <= 135:  # Nút Quit
                        pygame.quit()
                

                if is_off_screen(ground_group.sprites()[0]):
                    ground_group.remove(ground_group.sprites()[0])

                    new_ground = Ground(GROUND_WIDHT - 20)
                    ground_group.add(new_ground)


                bird.begin()
                ground_group.update()

                bird_group.draw(screen)
                ground_group.draw(screen)

                pygame.display.update()

            
            while start:
                selected_level = get_level(user)
                if(selected_level == 1):
                    SPEED = 15
                    GRAVITY = 5
                    GAME_SPEED = 15
                elif(selected_level == 2):
                    SPEED = 18
                    GRAVITY = 8
                    GAME_SPEED = 20
                else:
                    SPEED = 21
                    GRAVITY = 10
                    GAME_SPEED = 25
                
                fpsClock.tick(FPS)

                for event in pygame.event.get():
                    if event.type == QUIT:
                        pygame.quit()
                    if event.type == KEYDOWN:
                        if event.key == K_SPACE or event.key == K_UP:
                            bird.bump()
                            pygame.mixer.music.load(wing)
                            pygame.mixer.music.play()
                            spawn_powerup()

                        if event.key == K_b and bird.has_bullets:  # Nhấn B để bắn đạn
                            bullet = bird.shoot_bullet()
                            if num_bullet > 0: num_bullet-=1
                            if num_bullet <= 0: bird.has_bullets = False
                            if bullet: 
                                bullet_group.add(bullet)
                            # bullet = Bullet(bird.rect.right, bird.rect.centery)  # Tọa độ xuất phát của đạn
                            # bullet_group.add(bullet)     

                powerup_group.update()
                bullet_group.update()

                # Kiểm tra va chạm với vật phẩm
                if pygame.sprite.spritecollideany(bird, powerup_group):
                    powerup_group.empty()  # Xóa vật phẩm sau khi ăn
                    bird.has_bullets = True
                    num_bullet += 5


                # Kiểm tra va chạm đạn với ống 
                for bullet in bullet_group:
                    for pipe in pipe_group:
                        if bullet.rect.colliderect(pipe.rect) and not is_off_screen(pipe) and not is_off_screen(bullet):
                            bullet.kill()
                            pipe.kill()                             

                screen.blit(BACKGROUND, (0, 0))

                # Cập nhật, tịnh tiến ground
                if is_off_screen(ground_group.sprites()[0]):
                    ground_group.remove(ground_group.sprites()[0])

                    new_ground = Ground(GROUND_WIDHT - 20)
                    ground_group.add(new_ground) 

                # Cập nhật, tịnh tiến pipe
                if is_off_screen(pipe_group.sprites()[0]):
                    if len(pipe_group) >= 0 and len(pipe_group)%2 == 1:  # Kiểm tra xem nhóm có phần tử
                        pipe_group.remove(pipe_group.sprites()[0])
                    elif len(pipe_group) >= 0 and len(pipe_group)%2 == 0:
                        pipe_group.remove(pipe_group.sprites()[0])
                        pipe_group.remove(pipe_group.sprites()[0])

                    pipes = get_random_pipes(SCREEN_WIDHT * 2)

                    pipe_group.add(pipes[0])
                    pipe_group.add(pipes[1])

                    # Thả sâu giữa 2 ống mới
                    create_worm_between_pipes(pipes[0], pipes[1])
                
            
                bird_group.update()
                ground_group.update()
                pipe_group.update()
                update_worms()  # ăn sâu trước khi check_collision

                
                bird_group.draw(screen)
                pipe_group.draw(screen)
                ground_group.draw(screen)

                worm_group.draw(screen)
                powerup_group.draw(screen)
                bullet_group.draw(screen)

                draw_text(screen, user, 30, SCREEN_WIDHT // 10, 20, CORAL)
                # Tải hình viên đạn
                bullet_image = pygame.image.load('assets/sprites/bullet.png')

                # Lấy kích thước viên đạn (nếu cần căn chỉnh) 
                bullet_image = pygame.transform.scale(bullet_image, (16, 16))

                # Hiển thị viên đạn ngay bên dưới tên người dùng
                # Vị trí x = SCREEN_WIDHT // 10 (trùng với tên người dùng), y = 20 + kích thước font + khoảng cách
                screen.blit(bullet_image, (SCREEN_WIDHT // 18, 20 + 10))
                draw_text(screen, str(num_bullet), 30, SCREEN_WIDHT // 8, 20 + 20, CORAL)

                if num_bullet > 0:
                    draw_text(screen, "(press B)", 30, (SCREEN_WIDHT // 4) + 4, 20 + 20, CORAL)

                font = pygame.font.Font(None, 36)
                score_text = font.render(f"Score: {score}", True, WHITE)
                screen.blit(score_text, (SCREEN_WIDHT // 18, 20 + 30))

                pygame.display.update()

                # Kiểm tra va chạm
                # if can_penetrate == False or bird.is_upgraded == False:
                #     if check_collision():
                if pygame.sprite.spritecollideany(bird, ground_group) or (pygame.sprite.spritecollideany(bird, pipe_group) and (can_penetrate == False or bird.is_upgraded == False)):
                    pygame.mixer.music.load(hit)
                    pygame.mixer.music.play()

                    highscore = get_high_score(user)
                    if score > highscore:
                        update_highscore(user, score)
                    if not game_over_screen(score):  # Hiển thị màn hình Game Over
                        bird = Bird()
                        bird_group = pygame.sprite.Group()
                        bird_group.add(bird)
                        begin = True

                        pipe_group = pygame.sprite.Group()
                        for i in range(2):
                            pipes = get_random_pipes(SCREEN_WIDHT * i + 800)
                            pipe_group.add(pipes[0])
                            pipe_group.add(pipes[1])
                        start = False
                    else:
                        # Khởi động lại game
                        bird = Bird()
                        bird_group = pygame.sprite.Group()
                        bird_group.add(bird)
                        begin = True

                        pipe_group = pygame.sprite.Group()
                        for i in range(2):
                            pipes = get_random_pipes(SCREEN_WIDHT * i + 800)
                            pipe_group.add(pipes[0])
                            pipe_group.add(pipes[1])

                        score = 0  # Reset điểm
                        num_bullet = 0
        
        


