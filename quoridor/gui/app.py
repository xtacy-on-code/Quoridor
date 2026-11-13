"""Pygame front end: menu, board, walls, AI turns.

Controls
--------
Click a highlighted cell       move your pawn
Hover a groove, click          place a wall (preview shows if it is legal)
Right click                    rotate the wall when hovering a groove crossing
P                              show / hide both players' BFS shortest paths
U                              undo your last move (and the AI's reply)
Space                          pause / resume (AI vs AI)
R                              restart       Esc   back to menu
"""

import threading
import time

import pygame

from quoridor import pathfinding
from quoridor.ai import make_agent, LEVELS
from quoridor.board import GameState
from quoridor.config import SIZE, MAX_PLIES, GOAL_ROW
from quoridor.gui import theme as T


def lerp(a, b, t):
    return a + (b - a) * t


def blend(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


class Button:
    def __init__(self, rect, label, value=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = value if value is not None else label

    def draw(self, surf, font, selected=False, hover=False, accent=T.PLAYER_COLORS[0]):
        bg = accent if selected else (T.CELL_HOVER if hover else T.CELL_COLOR)
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        color = T.BG if selected else T.TEXT
        img = font.render(self.label, True, color)
        surf.blit(img, img.get_rect(center=self.rect.center))


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Quoridor AI")
        # Draw on a fixed-size canvas and scale it to fit small laptop screens.
        info = pygame.display.Info()
        self.scale = 1.0
        if info.current_w > 0 and info.current_h > 0:
            self.scale = min(1.0, info.current_w * 0.95 / T.WIDTH, info.current_h * 0.85 / T.HEIGHT)
        self.window_size = (int(T.WIDTH * self.scale), int(T.HEIGHT * self.scale))
        self.window = pygame.display.set_mode(self.window_size)
        self.screen = pygame.Surface((T.WIDTH, T.HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.Font(None, 72)
        self.font_mid = pygame.font.Font(None, 34)
        self.font = pygame.font.Font(None, 26)
        self.font_small = pygame.font.Font(None, 21)

        # menu choices
        self.mode = "Human vs AI"
        self.ai_level = "Medium"
        self.human_side = 0
        self.ai_levels = ["Medium", "Hard"]     # AI vs AI: bottom, top
        self.screen_name = "menu"

        self.show_paths = False
        self.rotate = "h"
        self.running = True

    # ------------------------------------------------------------------
    # Game setup
    # ------------------------------------------------------------------
    def start_game(self):
        self.state = GameState()
        if self.mode == "Human vs AI":
            self.controllers = [None, None]
            ai = 1 - self.human_side
            self.controllers[ai] = make_agent(self.ai_level)
            self.names = ["", ""]
            self.names[self.human_side] = "You"
            self.names[ai] = "%s AI" % self.ai_level
        else:
            self.controllers = [make_agent(self.ai_levels[0]), make_agent(self.ai_levels[1])]
            self.names = ["%s AI" % self.ai_levels[0], "%s AI" % self.ai_levels[1]]
        self.game_id = getattr(self, "game_id", 0) + 1
        self.thinking = False
        self.ai_result = None
        self.ai_stats = ["", ""]
        self.paused = False
        self.last_move_time = time.time()
        self.anim = None                     # (player, from_cell, to_cell, start_time)
        self.last_move = None
        self.screen_name = "game"

    def is_human_turn(self):
        return self.controllers[self.state.turn] is None and not self.game_over()

    def game_over(self):
        return self.state.winner() is not None or self.state.plies() >= MAX_PLIES

    # ------------------------------------------------------------------
    # AI turn on a background thread so the window never freezes
    # ------------------------------------------------------------------
    def maybe_start_ai(self):
        if self.game_over() or self.thinking or self.paused or self.anim:
            return
        agent = self.controllers[self.state.turn]
        if agent is None:
            return
        if self.mode == "AI vs AI" and time.time() - self.last_move_time < T.AI_MOVE_DELAY:
            return
        self.thinking = True
        snapshot = self.state.copy()
        game_id = self.game_id

        def work():
            move = agent.choose_move(snapshot)
            self.ai_result = (game_id, snapshot.plies(), move, agent)

        threading.Thread(target=work, daemon=True).start()

    def collect_ai(self):
        if self.ai_result is None:
            return
        game_id, plies, move, agent = self.ai_result
        self.ai_result = None
        self.thinking = False
        if game_id != self.game_id or plies != self.state.plies():
            return                                   # stale result after undo/restart
        p = self.state.turn
        if agent.depth_reached:
            self.ai_stats[p] = "depth %d  |  %s nodes  |  %.2fs" % (
                agent.depth_reached, format(agent.nodes, ","), agent.last_time)
        else:
            self.ai_stats[p] = "quick move  |  %.2fs" % agent.last_time
        self.play(move)

    def play(self, move):
        p = self.state.turn
        if move[0] == "move":
            self.anim = (p, self.state.pawns[p], (move[1], move[2]), time.time())
        self.state.apply(move)
        self.last_move = move
        self.last_move_time = time.time()

    # ------------------------------------------------------------------
    # Mouse -> board geometry
    # ------------------------------------------------------------------
    def cell_rect(self, r, c):
        return pygame.Rect(T.BOARD_X + c * T.STEP, T.BOARD_Y + r * T.STEP, T.CELL, T.CELL)

    def wall_rect(self, ori, r, c):
        x = T.BOARD_X + c * T.STEP
        y = T.BOARD_Y + r * T.STEP
        if ori == "h":
            return pygame.Rect(x + 2, y + T.CELL + 2, 2 * T.CELL + T.GAP - 4, T.GAP - 4)
        return pygame.Rect(x + T.CELL + 2, y + 2, T.GAP - 4, 2 * T.CELL + T.GAP - 4)

    def hover_target(self, pos):
        """What the mouse is over: ("cell", r, c), ("wall", ori, r, c) or None."""
        x = pos[0] - T.BOARD_X
        y = pos[1] - T.BOARD_Y
        if x < 0 or y < 0 or x >= T.BOARD_PX or y >= T.BOARD_PX:
            return None
        col, xin = divmod(x, T.STEP)
        row, yin = divmod(y, T.STEP)
        gap_x = xin >= T.CELL
        gap_y = yin >= T.CELL
        if not gap_x and not gap_y:
            return ("cell", row, col)

        def clamp(v):
            return max(0, min(SIZE - 2, v))

        if gap_y and not gap_x:      # between two rows -> horizontal wall
            c = col if xin >= T.CELL / 2 else col - 1
            return ("wall", "h", row, clamp(c))
        if gap_x and not gap_y:      # between two columns -> vertical wall
            r = row if yin >= T.CELL / 2 else row - 1
            return ("wall", "v", clamp(r), col)
        return ("wall", self.rotate, row, col)   # on a crossing: use rotate setting

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def mouse_pos(self):
        return self.to_canvas(pygame.mouse.get_pos())

    def to_canvas(self, pos):
        return (int(pos[0] / self.scale), int(pos[1] / self.scale))

    def handle_event(self, e):
        if hasattr(e, "pos"):
            e.pos = self.to_canvas(e.pos)
        if e.type == pygame.QUIT:
            self.running = False
        elif self.screen_name == "menu":
            self.menu_event(e)
        else:
            self.game_event(e)

    def game_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.screen_name = "menu"
                self.game_id += 1
                self.thinking = False
            elif e.key == pygame.K_r:
                self.start_game()
            elif e.key == pygame.K_p:
                self.show_paths = not self.show_paths
            elif e.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif e.key == pygame.K_u:
                self.undo()
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 3:
                self.rotate = "v" if self.rotate == "h" else "h"
            elif e.button == 1 and self.is_human_turn() and not self.anim:
                target = self.hover_target(e.pos)
                if target is None:
                    return
                if target[0] == "cell":
                    move = ("move", target[1], target[2])
                else:
                    move = target
                if self.state.is_legal(move):
                    self.play(move)

    def undo(self):
        """Take back your move and the AI's reply (or one move in a 2-human game)."""
        if self.thinking or self.mode != "Human vs AI":
            return
        while self.state.history:
            self.state.undo()
            if self.controllers[self.state.turn] is None:
                break
        self.anim = None
        self.last_move = self.state.history[-1][0] if self.state.history else None
        self.game_id += 1

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------
    def menu_layout(self):
        cx = T.WIDTH // 2
        y = 260
        rows = []
        modes = [Button((cx - 230, y, 220, 50), "Human vs AI"),
                 Button((cx + 10, y, 220, 50), "AI vs AI")]
        rows.append(("Mode", modes, "mode"))
        y += 110
        if self.mode == "Human vs AI":
            lv = [Button((cx - 230 + i * 160, y, 140, 50), name) for i, name in enumerate(LEVELS)]
            rows.append(("AI difficulty", lv, "ai_level"))
            y += 110
            side = [Button((cx - 230, y, 220, 50), "Move first (bottom)", 0),
                    Button((cx + 10, y, 220, 50), "Move second (top)", 1)]
            rows.append(("You play", side, "human_side"))
            y += 110
        else:
            for k, label in enumerate(["Amber AI (bottom, moves first)", "Cyan AI (top)"]):
                lv = [Button((cx - 230 + i * 160, y, 140, 50), name) for i, name in enumerate(LEVELS)]
                rows.append((label, lv, ("ai_levels", k)))
                y += 110
        start = Button((cx - 110, y + 20, 220, 58), "Start game")
        return rows, start

    def menu_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
            self.start_game()
        if e.type != pygame.MOUSEBUTTONDOWN or e.button != 1:
            return
        rows, start = self.menu_layout()
        if start.rect.collidepoint(e.pos):
            self.start_game()
            return
        for _, buttons, key in rows:
            for b in buttons:
                if b.rect.collidepoint(e.pos):
                    if isinstance(key, tuple):
                        self.ai_levels[key[1]] = b.value
                    else:
                        setattr(self, key, b.value)

    def draw_menu(self):
        s = self.screen
        s.fill(T.BG)
        cx = T.WIDTH // 2
        title = self.font_big.render("QUORIDOR", True, T.TEXT)
        s.blit(title, title.get_rect(center=(cx, 120)))
        sub = self.font.render("Alpha-Beta search  +  BFS path evaluation", True, T.MUTED)
        s.blit(sub, sub.get_rect(center=(cx, 170)))
        pygame.draw.circle(s, T.PLAYER_COLORS[0], (cx - 175, 121), 12)
        pygame.draw.circle(s, T.PLAYER_COLORS[1], (cx + 175, 121), 12)

        mouse = self.mouse_pos()
        rows, start = self.menu_layout()
        for label, buttons, key in rows:
            img = self.font_small.render(label.upper(), True, T.MUTED)
            s.blit(img, (buttons[0].rect.x, buttons[0].rect.y - 26))
            for b in buttons:
                if isinstance(key, tuple):
                    selected = self.ai_levels[key[1]] == b.value
                    accent = T.PLAYER_COLORS[key[1]]
                else:
                    selected = getattr(self, key) == b.value
                    accent = T.PLAYER_COLORS[0]
                b.draw(s, self.font, selected, b.rect.collidepoint(mouse), accent)
        start.draw(s, self.font_mid, True, False, T.WALL)
        hint = self.font_small.render("Press Enter to start", True, T.MUTED)
        s.blit(hint, hint.get_rect(center=(cx, start.rect.bottom + 28)))

    # ------------------------------------------------------------------
    # Board drawing
    # ------------------------------------------------------------------
    def pawn_pixel(self, p):
        r, c = self.state.pawns[p]
        if self.anim and self.anim[0] == p:
            _, (r0, c0), (r1, c1), t0 = self.anim
            t = min(1.0, (time.time() - t0) / 0.16)
            t = 1 - (1 - t) ** 3                     # ease-out
            if t >= 1.0:
                self.anim = None
            r, c = lerp(r0, r1, t), lerp(c0, c1, t)
        return (T.BOARD_X + c * T.STEP + T.CELL / 2, T.BOARD_Y + r * T.STEP + T.CELL / 2)

    def draw_board(self):
        s = self.screen
        s.fill(T.BG)
        pad = 12
        pygame.draw.rect(s, T.BOARD_BG, (T.BOARD_X - pad, T.BOARD_Y - pad,
                                         T.BOARD_PX + 2 * pad, T.BOARD_PX + 2 * pad),
                         border_radius=16)

        mouse = self.mouse_pos()
        target = self.hover_target(mouse) if self.is_human_turn() and not self.anim else None
        dests = set(self.state.pawn_moves()) if self.is_human_turn() and not self.anim else set()

        for r in range(SIZE):
            for c in range(SIZE):
                color = T.CELL_COLOR
                for p in (0, 1):
                    if r == GOAL_ROW[p]:
                        color = blend(T.CELL_COLOR, T.PLAYER_COLORS[p], 0.13)
                if target and target[0] == "cell" and (target[1], target[2]) == (r, c) and (r, c) in dests:
                    color = blend(color, T.PLAYER_COLORS[self.state.turn], 0.35)
                pygame.draw.rect(s, color, self.cell_rect(r, c), border_radius=8)
                if (r, c) in dests:
                    pygame.draw.circle(s, blend(T.CELL_COLOR, T.PLAYER_COLORS[self.state.turn], 0.6),
                                       self.cell_rect(r, c).center, 7)

        # coordinates
        for i in range(SIZE):
            img = self.font_small.render(chr(ord("a") + i), True, T.MUTED)
            s.blit(img, img.get_rect(center=(T.BOARD_X + i * T.STEP + T.CELL / 2,
                                             T.BOARD_Y + T.BOARD_PX + 26)))
            img = self.font_small.render(str(SIZE - i), True, T.MUTED)
            s.blit(img, img.get_rect(center=(T.BOARD_X - 28, T.BOARD_Y + i * T.STEP + T.CELL / 2)))

        if self.show_paths:
            self.draw_paths()

        # walls
        for ori, walls in (("h", self.state.h_walls), ("v", self.state.v_walls)):
            for (r, c) in walls:
                color = T.WALL
                if self.last_move == ("wall", ori, r, c):
                    color = blend(T.WALL, T.PLAYER_COLORS[1 - self.state.turn], 0.45)
                pygame.draw.rect(s, color, self.wall_rect(ori, r, c), border_radius=4)

        # wall preview
        if target and target[0] == "wall":
            legal = self.state.is_legal(target)
            color = T.PLAYER_COLORS[self.state.turn] if legal else T.ILLEGAL
            if self.state.walls_left[self.state.turn] == 0:
                color = T.ILLEGAL
            ghost = pygame.Surface((T.WIDTH, T.HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(ghost, color + (170,), self.wall_rect(*target[1:]), border_radius=4)
            s.blit(ghost, (0, 0))

        # pawns
        for p in (0, 1):
            x, y = self.pawn_pixel(p)
            col = T.PLAYER_COLORS[p]
            pygame.draw.circle(s, blend(col, T.BG, 0.55), (x, y + 3), T.CELL * 0.33)
            pygame.draw.circle(s, col, (x, y), T.CELL * 0.33)
            pygame.draw.circle(s, blend(col, (255, 255, 255), 0.35), (x, y), T.CELL * 0.33, 3)
            if self.state.turn == p and not self.game_over():
                pygame.draw.circle(s, col, (x, y), T.CELL * 0.45, 2)

        if self.game_over():
            self.draw_game_over()

    def draw_paths(self):
        overlay = pygame.Surface((T.WIDTH, T.HEIGHT), pygame.SRCALPHA)
        for p in (0, 1):
            path = pathfinding.shortest_path(self.state, p)
            if not path:
                continue
            pts = [self.cell_rect(r, c).center for (r, c) in path]
            if len(pts) > 1:
                pygame.draw.lines(overlay, T.PLAYER_COLORS[p] + (150,), False, pts, 4)
            for pt in pts[1:]:
                pygame.draw.circle(overlay, T.PLAYER_COLORS[p] + (190,), pt, 6)
        self.screen.blit(overlay, (0, 0))

    def draw_game_over(self):
        w = self.state.winner()
        if w is None:
            title, color = "Draw (move limit)", T.TEXT
        else:
            if self.mode == "Human vs AI":
                title = "You win!" if self.controllers[w] is None else "%s wins" % self.names[w]
            else:
                title = "%s (%s) wins" % (self.names[w], T.PLAYER_NAMES[w])
            color = T.PLAYER_COLORS[w]
        box = pygame.Rect(0, 0, 460, 140)
        box.center = (T.BOARD_X + T.BOARD_PX // 2, T.BOARD_Y + T.BOARD_PX // 2)
        shade = pygame.Surface((T.WIDTH, T.HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 120))
        self.screen.blit(shade, (0, 0))
        pygame.draw.rect(self.screen, T.BOARD_BG, box, border_radius=16)
        pygame.draw.rect(self.screen, color, box, 3, border_radius=16)
        img = self.font_mid.render(title, True, color)
        self.screen.blit(img, img.get_rect(center=(box.centerx, box.centery - 18)))
        img = self.font_small.render("R  play again      Esc  menu", True, T.MUTED)
        self.screen.blit(img, img.get_rect(center=(box.centerx, box.centery + 28)))

    # ------------------------------------------------------------------
    # Side panel
    # ------------------------------------------------------------------
    def draw_panel(self):
        s = self.screen
        x = T.PANEL_X
        y = T.BOARD_Y - 12

        # status line
        if self.game_over():
            status = "Game over"
        elif self.paused:
            status = "Paused (Space to resume)"
        elif self.thinking:
            dots = "." * (int(time.time() * 3) % 4)
            status = "%s is thinking%s" % (self.names[self.state.turn], dots)
        elif self.is_human_turn():
            status = "Your turn"
        else:
            status = "%s to move" % self.names[self.state.turn]
        img = self.font_mid.render(status, True, T.TEXT)
        s.blit(img, (x, y))
        y += 48

        for p in (0, 1):
            card = pygame.Rect(x, y, T.PANEL_W, 132)
            border = T.PLAYER_COLORS[p] if self.state.turn == p and not self.game_over() else T.LINE
            pygame.draw.rect(s, T.BOARD_BG, card, border_radius=14)
            pygame.draw.rect(s, border, card, 2, border_radius=14)
            pygame.draw.circle(s, T.PLAYER_COLORS[p], (x + 24, y + 28), 10)
            img = self.font.render("%s  (%s)" % (self.names[p], T.PLAYER_NAMES[p]), True, T.TEXT)
            s.blit(img, (x + 44, y + 19))

            dist = pathfinding.distance(self.state, p)
            img = self.font_small.render("Steps to goal (BFS)", True, T.MUTED)
            s.blit(img, (x + 18, y + 55))
            img = self.font_mid.render(str(dist), True, T.TEXT)
            s.blit(img, (x + T.PANEL_W - 18 - img.get_width(), y + 50))

            img = self.font_small.render("Walls left", True, T.MUTED)
            s.blit(img, (x + 18, y + 84))
            for i in range(10):
                bx = x + 110 + i * 17
                filled = i < self.state.walls_left[p]
                pygame.draw.rect(s, T.WALL if filled else T.LINE, (bx, y + 82, 11, 18), border_radius=3)

            img = self.font_small.render(self.ai_stats[p], True, T.MUTED)
            s.blit(img, (x + 18, y + 108))
            y += 148

        # advantage bar: difference in path lengths
        d0 = pathfinding.distance(self.state, 0)
        d1 = pathfinding.distance(self.state, 1)
        adv = max(-8, min(8, d1 - d0))     # positive = Amber ahead
        img = self.font_small.render("Race advantage (BFS steps)", True, T.MUTED)
        s.blit(img, (x, y))
        if d1 == d0:
            label, lcol = "even", T.TEXT
        else:
            lead = 0 if d1 > d0 else 1
            label, lcol = "%s +%d" % (T.PLAYER_NAMES[lead], abs(d1 - d0)), T.PLAYER_COLORS[lead]
        img = self.font_small.render(label, True, lcol)
        s.blit(img, (x + T.PANEL_W - img.get_width(), y))
        bar = pygame.Rect(x, y + 22, T.PANEL_W, 12)
        pygame.draw.rect(s, T.PLAYER_COLORS[1], bar, border_radius=6)
        split = bar.x + bar.w * (0.5 + adv / 16)
        pygame.draw.rect(s, T.PLAYER_COLORS[0], (bar.x, bar.y, split - bar.x, bar.h), border_radius=6)
        y += 60

        help_lines = [
            ("Click cell", "move pawn"),
            ("Hover groove", "place wall"),
            ("Right click", "rotate wall at crossing"),
            ("P", "show BFS paths" + ("  (on)" if self.show_paths else "")),
            ("U", "undo"),
            ("Space", "pause AI vs AI"),
            ("R / Esc", "restart / menu"),
        ]
        for key, what in help_lines:
            img = self.font_small.render(key, True, T.TEXT)
            s.blit(img, (x, y))
            img = self.font_small.render(what, True, T.MUTED)
            s.blit(img, (x + 120, y))
            y += 22
        img = self.font_small.render("Move %d" % (self.state.plies() + 1), True, T.MUTED)
        s.blit(img, (x, T.HEIGHT - 40))

    # ------------------------------------------------------------------
    def draw(self):
        if self.screen_name == "menu":
            self.draw_menu()
        else:
            self.draw_board()
            self.draw_panel()

    def run(self):
        while self.running:
            for e in pygame.event.get():
                self.handle_event(e)
            if self.screen_name == "game":
                self.collect_ai()
                self.maybe_start_ai()
            self.draw()
            if self.scale == 1.0:
                self.window.blit(self.screen, (0, 0))
            else:
                self.window.blit(pygame.transform.smoothscale(self.screen, self.window_size), (0, 0))
            pygame.display.flip()
            self.clock.tick(T.FPS)
        pygame.quit()
