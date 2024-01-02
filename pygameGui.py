import pygame as pg

pg.init()

class Button:
    def __init__(self, x, y, width, height, color, selectedColor, textColor, text, size, radius):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.selectedColor = selectedColor
        self.textColor = textColor
        self.text = text
        self.radius = radius
        self.clicked = False
        self.font = pg.font.SysFont("Arial", size)
        self.size = size

    def draw(self, screen):
        if self.clicked: pg.draw.rect(screen, self.selectedColor, (self.x, self.y, self.width, self.height), border_radius=self.radius)
        else: pg.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height), border_radius=self.radius)
        screen.blit(self.font.render(self.text, True, self.textColor), (self.x + self.size/2, self.y + self.size/2))