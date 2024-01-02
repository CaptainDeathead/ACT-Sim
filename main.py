import pygame as pg
import math
import random
import pathfinder
import pygameGui as pgui
import time
#import cProfile
import asyncio

pg.init()

planeStats = {
    "Cessna 152": {
        "maxspeed": 120,
        "cruisespeed": 105,
        "stallspeed": 40,
        "approachspeed": 60,
        "tkfspeed": 55,
        "waypointRadius": 10,
        "image": "images/GAPlane.png"
    },
    "Piper PA-28 Cherokee": {
        "maxspeed": 130,
        "cruisespeed": 123,
        "stallspeed": 50,
        "approachspeed": 67,
        "tkfspeed": 60,
        "waypointRadius": 12,
        "image": "images/GAPlane.png"
    },
    "Piper PA-32 Cherokee": {
        "maxspeed": 180,
        "cruisespeed": 145,
        "stallspeed": 55,
        "approachspeed": 80,
        "tkfspeed": 65,
        "waypointRadius": 13,
        "image": "images/GAPlane.png"
    },
    "Cessna 172": {
        "maxspeed": 120,
        "cruisespeed": 110,
        "stallspeed": 45,
        "approachspeed": 65,
        "tkfspeed": 60,
        "waypointRadius": 12,
        "image": "images/GAPlane.png"
    },
    "Beechcraft King Air 360": {
        "maxspeed": 220,
        "cruisespeed": 180,
        "stallspeed": 81,
        "approachspeed": 100,
        "tkfspeed": 100,
        "waypointRadius": 19,
        "image": "images/TwinPlane.png"
    },
    "Cessna Citation Longitude": {
        "maxspeed": 240,
        "cruisespeed": 200,
        "stallspeed": 82,
        "approachspeed": 150,
        "tkfspeed": 135,
        "waypointRadius": 21,
        "image": "images/RJet.png"
    },
    "Airbus A320 Neo": {
        "maxspeed": 260,
        "cruisespeed": 230,
        "stallspeed": 127,
        "approachspeed": 160,
        "tkfspeed": 145,
        "waypointRadius": 27,
        "image": "images/jetpix.png"
    }
}

phonetic_dict = {
    'a': 'alpha',
    'b': 'bravo',
    'c': 'charlie',
    'd': 'delta',
    'e': 'echo',
    'f': 'foxtrot',
    'g': 'golf',
    'h': 'hotel',
    'i': 'india',
    'j': 'juliet',
    'k': 'kilo',
    'l': 'lima',
    'm': 'mike',
    'n': 'november',
    'o': 'oscar',
    'p': 'papa',
    'q': 'quebec',
    'r': 'romeo',
    's': 'sierra',
    't': 'tango',
    'u': 'uniform',
    'v': 'victor',
    'w': 'whiskey',
    'x': 'x-ray',
    'y': 'yankee',
    'z': 'zulu'
}

SCALE = 1000

def _genCallsign(length):
        callsign = ""
        for i in range(length):
            callsign += chr(random.randint(65, 65+25))
        return callsign

def _formatNum(num):
    if '-' in num:
        num = str(360 + int(num))

    if len(num) == 2:
        num = '0' + num
    elif len(num) == 1:
        num = '00' + num

    return num

def printout(text):
    try: window.customBar.output.append(text)
    except: pass

class Particle:
    def __init__(self, x, y, rotation, color, liveTime):
        self.x = x
        self.y = y
        self.rotation = rotation
        self.color = color
        self.liveTime = liveTime
        self.startTime = time.time()

    def draw(self, screen):
        if time.time() - self.startTime > self.liveTime: return True
        else:
            self.x += math.cos(math.radians(self.rotation))
            self.y += math.sin(math.radians(self.rotation))
            pg.draw.rect(screen, self.color, (self.x, self.y, 3, 3))

class Explosion:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.particles = [Particle(self.x, self.y, random.randint(0, 360), (255, 60, 0), 2) for i in range(60)]
        self.startTime = time.time()

    def draw(self, screen):
        if time.time() - self.startTime < 1:
            self.particles.extend([Particle(self.x, self.y, random.randint(0, 360), (255, 60, 0), 2) for i in range(60)])
        for particle in self.particles:
            if particle.draw(screen): self.particles.remove(particle)

class Plane:
    def __init__(self, x, y, rotation, planeType, wpts):
        self.x = x
        self.y = y
        self.rotation = rotation - 90
        self.stats = planeStats[planeType]
        self.planeType = planeType
        self.callsign = _genCallsign(3)
        self.callsignText = pg.font.SysFont("Arial", 10)
        self.wpts = wpts
        self.flightPath = self.calculateFlightPath(True)
        self.image = pg.transform.scale(pg.image.load(self.stats["image"]).convert_alpha(), (12, 12))
        self.direction = [math.cos(math.radians(self.rotation)), math.sin(math.radians(self.rotation))]
        self.speed = self.stats["cruisespeed"]
        self.tower = True
        self.rotationChange = rotation - 90
        self.focused = False
        self.taxiways = {
            0: ((770, 220), (758, 193), (743, 177), (674, 175)),
            1: ((663, 220), (651, 208), (650, 186)),
            2: ((535, 220), (545, 212), (547, 184)),
            3: ((428, 200), (431, 206), (458, 178), (528, 175))
        }
        self.taxiway = None
        self.taxiIndex = 0
        self.gates = [553, 577, 600, 623, 645, 667]
        self.gateIndex = random.randint(0, 5)
        self.foundTaxi = False
        self.foundGate = False
        self.parked = False
        self.paused = False
        self.parkTime = None
        self.takingOff = False
        self.rumbling = False
        self.takingOffFunc = False
        self.goingAround = False

    def move(self):
        if self.takingOff:
            self.takeOff(False)
            return "ok"
        if self.x < 0 or self.x > 400 or self.y < 0 or self.y > 400: return "out"
        if len(self.flightPath) > 0:
            self.rotationChange = 180-math.atan2(self.flightPath[0][1]*50-6-self.y, self.flightPath[0][0]*50+16-self.x) * 57.2957795
            if self.rotation < 0: self.rotation += 360
            if abs(self.flightPath[0][1]*50-5-self.y + self.flightPath[0][0]*50+16-self.x) < self.stats["waypointRadius"]:
                #for waypoint in self.wpts:
                #    if (int((self.wpts[waypoint][0])/50), int((self.wpts[waypoint][1])/50)) == self.flightPath[0]: printout(f"Waypoint '{waypoint}' completed by {self.callsign}.")
                self.flightPath.pop(0)
        elif self.goingAround:
            self.flightPath.append((3.5, 4))
            self.goingAround = False
        else:
            self.flightPath.append((3.5, 4))
            #printout(f"{self.callsign} is attempting a recalculated approach.")
        if not self.rumbling and not self.goingAround and abs(math.sqrt((200-self.y)**2 + (200-self.x)**2)) < self.stats['waypointRadius'] + 1:
            self.rotation = 0
            self.rotationChange = 0
            self.x = 800
            self.y = 232
            printout(f"{self.callsign} ground handoff.")
            self.tower = False
            self.speed = self.stats["approachspeed"]

            return "groundHandoff"

        rotateDistLeft = self.rotationChange-self.rotation
        if rotateDistLeft < -180: rotateDistLeft = abs(rotateDistLeft+180)
        elif rotateDistLeft > 180: rotateDistLeft = 180 - rotateDistLeft

        #printout(str((int(self.rotation), int(self.rotationChange), int(rotateDistLeft))))
        
        if rotateDistLeft < 180 and rotateDistLeft > 0: self.rotation += 1 / 2.25
        elif rotateDistLeft > -180 and rotateDistLeft < 0: self.rotation -= 1 / 2.25
        self.direction = [math.cos(math.radians(self.rotation)), math.sin(math.radians(self.rotation))]
        self.x -= self.direction[0] * self.speed / SCALE
        self.y += self.direction[1] * self.speed / SCALE

        return "ok"

    def taxi(self, gatesUsage, stopY):
        if self.takingOffFunc:
            self.takeOff(False)
            return
        usedGateIndex = None
        if self.parked and time.time() - self.parkTime > 5:
            self.parked = False
            self.taxiway = list(self.taxiways[0])
            self.taxiway.reverse()
            self.taxiIndex = 0
            self.rotation = 90
            self.takingOff = True
            usedGateIndex = self.gateIndex
            printout(f"{self.callsign} is taxing to the runway.")
        elif self.speed > 20: self.speed *= 0.995
        elif self.paused or (self.takingOff and self.x > 700 and stopY != None and abs(stopY - self.y) < 15):
            self.speed = 0
            return None
        else:
            self.speed = 20
            if self.taxiway == None:
                for taxiway in self.taxiways:
                    if self.taxiways[taxiway][0][0] < self.x:
                        self.taxiway = self.taxiways[taxiway]
                        printout(f"{self.callsign} is taxing via taxiway '{phonetic_dict[chr(65+taxiway).lower()]}'.")
                        break
        
            if self.taxiIndex == 0 and abs((self.taxiway[self.taxiIndex][0]-self.x)) < 5:
                self.rotationChange = 180-math.atan2(self.taxiway[0][1]-5-self.y, self.taxiway[0][0]-6-self.x) * 57.2957795
                self.foundTaxi = True
                self.taxiIndex = 1
            elif self.foundTaxi == False:
                self.rotationChange = 0
                self.rotation = 0
            elif self.taxiIndex == 'hold':
                self.rotation = 90
                self.speed = 0
            elif self.taxiIndex == 'gate':
                if self.foundGate == False:
                    filtered_list = [(item, index) for index, item in enumerate(gatesUsage) if not item]
                    random_gate, self.gateIndex = random.choice(filtered_list)
                    self.foundGate = True
                    usedGateIndex = self.gateIndex
                    printout(f"{self.callsign} is taxing to gate '{phonetic_dict[chr(65+usedGateIndex).lower()]}'.")
                self.rotationChange = 180-math.atan2(159-self.y, self.gates[self.gateIndex]-self.x) * 57.2957795
                if abs(math.sqrt((159-self.y)**2 + (self.gates[self.gateIndex]-self.x)**2)) < 2:
                    self.speed = 0
                    if self.taxiIndex == 'gate':
                        self.rotation = 270
                        self.parked = True
                        self.parkTime = time.time()
                        self.taxiIndex = 'gateDone'
            elif self.taxiIndex == 'gateDone':
                self.speed = 0
                self.rotation = 270
            else:
                if self.taxiIndex < len(self.taxiway): self.rotationChange = 180-math.atan2(self.taxiway[self.taxiIndex][1]-self.y, self.taxiway[self.taxiIndex][0]-6-self.x) * 57.2957795

        if self.rotation < 0: self.rotation += 360

        rotateDistLeft = self.rotationChange-self.rotation
        if rotateDistLeft < -180: rotateDistLeft = abs(rotateDistLeft+180)
        elif rotateDistLeft > 180: rotateDistLeft = 180 - rotateDistLeft

        #printout(str((int(self.rotation), int(self.rotationChange), int(rotateDistLeft))))
        
        if rotateDistLeft < 180 and rotateDistLeft > 0: self.rotation += min(3, abs(self.rotationChange - self.rotation)/10)
        elif rotateDistLeft > -180 and rotateDistLeft < 0: self.rotation -= min(3, abs(self.rotationChange - self.rotation)/10)
        self.direction = [math.cos(math.radians(self.rotation)), math.sin(math.radians(self.rotation))]
        self.x -= self.direction[0] * self.speed / (SCALE / 10)
        self.y += self.direction[1] * self.speed / (SCALE / 10)

        if self.takingOff and self.taxiIndex == len(self.taxiway):
            self.taxiIndex = 'hold'
        elif self.taxiway and self.taxiIndex == len(self.taxiway):
            self.taxiIndex = 'gate'
        elif self.taxiway and type(self.taxiIndex) != str and abs(math.sqrt((self.taxiway[self.taxiIndex][1]-self.y)**2 + (self.taxiway[self.taxiIndex][0]-6-self.x)**2)) < 1:
            self.taxiIndex += 1
            #printout(str(self.taxiIndex))

        return usedGateIndex
    
    def takeOff(self, firstTime):
        self.takingOffFunc = True
        if self.rumbling:
            self.speed += 0.35
            self.rotation = 0
            if self.speed > self.stats["tkfspeed"]:
                self.x = 200
                self.y = 200
                if random.randint(0, 1) == 0: endPos = ((random.randint(0, 8), random.choice([-4, 12])))
                else: endPos = ((-5, random.randint(0, 8)))
                self.flightPath = [endPos]
                self.speed = self.stats["cruisespeed"]
                self.takingOff = False
                self.tower = True
            self.direction = [math.cos(math.radians(self.rotation)), math.sin(math.radians(self.rotation))]
            self.x -= self.direction[0] * self.speed / (SCALE / 10)
            self.y += self.direction[1] * self.speed / (SCALE / 10)
            return
        self.speed = 10
        self.rotationChange = 180-math.atan2(232-self.y, 750-self.x) * 57.2957795
        if self.rotation < 0: self.rotation += 360

        rotateDistLeft = self.rotationChange-self.rotation
        if rotateDistLeft < -180: rotateDistLeft = abs(rotateDistLeft+180)
        elif rotateDistLeft > 180: rotateDistLeft = 180 - rotateDistLeft
        
        if rotateDistLeft < 180 and rotateDistLeft > 0: self.rotation += 2
        elif rotateDistLeft > -180 and rotateDistLeft < 0: self.rotation -= 2
        self.direction = [math.cos(math.radians(self.rotation)), math.sin(math.radians(self.rotation))]
        self.x -= self.direction[0] * self.speed / (SCALE / 10)
        self.y += self.direction[1] * self.speed / (SCALE / 10)

        if abs(math.sqrt((232-self.y)**2 + (750-self.x)**2)) < 2: self.rumbling = True

    def calculateFlightPath(self, approach):
        if approach:
            matrix = []
            for y in range(9):
                matrix.append([])
                for x in range(9):
                    if x > 3 and x < 5 and y == 4: matrix[y].append(0)
                    else: matrix[y].append(1)
            flightPath = pathfinder.findPath(matrix, (int(self.x / 50), int(self.y / 50)), (5, 4))
            flightPath.append((3.5, 4))
            print(f"Flight path for {self.callsign}: {flightPath}")
        return flightPath

    def draw(self, screen, mousePos):
        if abs(math.sqrt((mousePos[1]-self.y-8)**2 + (mousePos[0]-self.x)**2)) < 20:
            self.focused = True
        else:
            self.focused = False
        screen.blit(pg.transform.rotate(self.image, self.rotation), (self.x, self.y))
        screen.blit(self.callsignText.render("VH-" + self.callsign, True, (255, 255, 255)), (self.x + 10, self.y + 10))
        if self.focused:
            screen.blit(self.callsignText.render(f"Type: {self.planeType}", True, (255, 255, 255)), (self.x + 10, self.y + 20))
            screen.blit(self.callsignText.render(f"Speed: {int(self.speed)}kts", True, (255, 255, 255)), (self.x + 10, self.y + 30))
            screen.blit(self.callsignText.render(f"Heading: {_formatNum(str(int(360-(self.rotation+90))))}°", True, (255, 255, 255)), (self.x + 10, self.y + 40))
        if len(self.flightPath) > 0 and self.tower and not self.takingOff:
            pg.draw.line(screen, (255, 0, 255), (self.x+8, self.y+8), (self.flightPath[0][0]*50+25, self.flightPath[0][1]*50))
            for i in range(1, len(self.flightPath)):
                pg.draw.line(screen, (255, 0, 255), (self.flightPath[i-1][0]*50+25, self.flightPath[i-1][1]*50), (self.flightPath[i][0]*50+25, self.flightPath[i][1]*50))
        #for waypoint in self.wpts:
        #    if (int((self.wpts[waypoint][0])/50), int((self.wpts[waypoint][1])/50)) in self.flightPath:
        #        pg.draw.circle(screen, (255, 255, 255), self.wpts[waypoint], 4)
        #        screen.blit(self.callsignText.render(waypoint, True, (255, 255, 255)), (self.wpts[waypoint][0] + 5, self.wpts[waypoint][1] + 5))

class Tower:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 400
        self.height = 400
        self.particles = []

    def draw(self, screen, planes, mousePos):
        pg.draw.line(screen, (255, 255, 255), (195, 200), (205, 200), 2)
        crashes = 0

        arrivals = 0
        departures = 0

        for particle in self.particles:
            particle.draw(screen)

        for plane in planes:
            status = plane.move()
            if status == "out":
                planes.pop(planes.index(plane))
                if plane.rumbling: departures += 1
            elif status == "groundHandoff": arrivals += 1
            plane.draw(screen, mousePos)
            for otherplane in planes:
                if otherplane == plane: continue
                if abs(math.sqrt((otherplane.y-plane.y)**2 + (otherplane.x-plane.x)**2)) < 5:
                    printout(f"Oh no! {2} aircraft appear to have vanished :(")
                    self.particles.append(Explosion(plane.x, plane.y, (255, 60, 0)))
                    crashes += 1
                    planes.pop(planes.index(plane))
                    planes.pop(planes.index(otherplane))
                    break

        return planes, crashes, arrivals, departures
    
class Ground:
    def __init__(self):
        self.x = 400
        self.y = 0
        self.width = 400
        self.height = 400
        self.airport = pg.transform.scale(pg.image.load('images/runway.png').convert_alpha(), (360, 100))
        self.gatesUsage = [False for i in range(6)]
        self.particles = []
        
    def draw(self, screen, planes, mousePos):
        pg.draw.rect(screen, (0, 0, 0), (400, 0, 400, 400))
        screen.blit(self.airport, (420, 150))
        crashes = 0
        planesInFront = []

        for particle in self.particles: particle.draw(screen)

        for plane in planes:
            if plane.takingOff and not plane.rumbling:
                planesInFront.append((planes.index(plane), plane.y))
        
        planesInFront.sort(key=lambda tup: tup[1])

        for plane in planes:
            sortedIndex = 0
            stopY = None
            for i, (j, y) in enumerate(planesInFront):
                if j == planes.index(plane):
                    sortedIndex = i
                    break
            if sortedIndex < len(planesInFront) - 1: stopY = planesInFront[sortedIndex+1][1]
            gateUsageIndex = plane.taxi(self.gatesUsage, stopY)
            plane.draw(screen, mousePos)
            if gateUsageIndex != None: self.gatesUsage[gateUsageIndex] = not self.gatesUsage[gateUsageIndex]
            if plane.speed > 0:
                for otherplane in planes:
                    if otherplane == plane or otherplane.speed == 0: continue
                    if abs(math.sqrt((otherplane.y-plane.y)**2 + (otherplane.x-plane.x)**2)) < 5:
                        printout(f"Oh no! {2} aircraft appear to have vanished :(")
                        self.particles.append(Explosion(plane.x, plane.y, (255, 60, 0)))
                        crashes += 1
                        planes.pop(planes.index(plane))
                        planes.pop(planes.index(otherplane))
                        break

        return planes, crashes

class CustomisationBar:
    def __init__(self):
        self.width = 800
        self.height = 200
        self.bg = (150, 150, 150)
        self.outputText = pg.font.SysFont("Arial", 10)
        self.output = []
        self.speedUpButton = pgui.Button(10, 410, 80, 30, (255, 0, 0), (255, 100, 100), (255, 255, 255), "Speed Up", 15, 5)
        self.slowDownButton = pgui.Button(10, 450, 90, 30, (0, 0, 255), (100, 100, 255), (255, 255, 255), "Slow Down", 15, 5)
        self.taxiPauseButton = pgui.Button(10, 490, 143, 30, (255, 85, 0), (255, 185, 100), (255, 255, 255), "Stop / Resume Taxi", 15, 5)
        self.tkfGoAroundButton = pgui.Button(10, 530, 120, 30, (0, 200, 0), (100, 255, 100), (255, 255, 255), "Tkf / Go Around", 15, 5)
        self.selectedPlane = None
        self.selectedPlaneLbl = "Selected plane: None"
        self.selectedPlaneName = ''
        self.selectedPlaneCallsign = "Callsign: --"
        self.selectedPlaneSpeed = "Speed: --"
        self.selectedPlaneHeading = "Heading: --"
        self.crashes = "Crashes: 0"
        self.arrivals = "Arrivals: 0"
        self.departures = "Departures: 0"
        self.trafficSpawnTime = "Next plane in: 40s"
        self.lastDraw = time.time()
        self.font20 = pg.font.SysFont("Arial", 20)
        self.font15 = pg.font.SysFont("Arial", 15)

    def draw(self, screen):
        pg.draw.rect(screen, self.bg, (0, 400, 800, 200))
        pg.draw.rect(screen, (200, 200, 200), (510, 410, 280, 180))
        while len(self.output) > 16:
            self.output.pop(0)
        for i in range(len(self.output)):
            if i == 0: screen.blit(self.outputText.render(self.output[i], True, (125, 125, 125)), (520, 420+i*10))
            elif i == 1: screen.blit(self.outputText.render(self.output[i], True, (100, 100, 100)), (520, 420+i*10))
            elif i == 2: screen.blit(self.outputText.render(self.output[i], True, (75, 75, 75)), (520, 420+i*10))
            else: screen.blit(self.outputText.render(self.output[i], True, (0, 0, 0)), (520, 420+i*10))
        self.speedUpButton.draw(screen)
        self.slowDownButton.draw(screen)
        self.taxiPauseButton.draw(screen)
        self.tkfGoAroundButton.draw(screen)
        screen.blit(self.font20.render(self.selectedPlaneLbl, True, (255, 255, 255)), (160, 415))
        screen.blit(self.font15.render(self.selectedPlaneCallsign, True, (255, 255, 255)), (160, 455))
        screen.blit(self.font15.render(self.selectedPlaneSpeed, True, (255, 255, 255)), (160, 475))
        screen.blit(self.font15.render(self.selectedPlaneHeading, True, (255, 255, 255)), (160, 495))
        screen.blit(self.font15.render('---------- Plane Stats ----------', True, (195, 195, 195)), (160, 515))
        if self.selectedPlaneName != '':
            screen.blit(self.font15.render(f'Max Speed: {planeStats[self.selectedPlaneName]["maxspeed"]}kts', True, (255, 255, 255)), (160, 535))
            screen.blit(self.font15.render(f'Cruise Speed: {planeStats[self.selectedPlaneName]["cruisespeed"]}kts', True, (255, 255, 255)), (160, 555))
            screen.blit(self.font15.render(f'Stall Speed: {planeStats[self.selectedPlaneName]["stallspeed"]}kts', True, (255, 255, 255)), (160, 575))
        screen.blit(self.font15.render(self.crashes, True, (255, 255, 255)), (300, 455))
        screen.blit(self.font15.render(self.arrivals, True, (255, 255, 255)), (300, 475))
        screen.blit(self.font15.render(self.departures, True, (255, 255, 255)), (300, 495))
        screen.blit(self.font15.render(self.trafficSpawnTime, True, (255, 255, 255)), (380, 575))

class Window:
    def __init__(self):
        self.screen = pg.display.set_mode((800, 600))
        pg.display.set_caption("ACT")
        self.wpts = {}
        self.usedWptNames = []
        self._initWpts()
        #self.groundWpts = 
        self.planes = [Plane(random.randint(20, 380), random.randint(20, 380), 0, random.choice(list(planeStats.keys())), self.wpts) for i in range(4)]
        #self.planes = [Plane(random.randint(20, 380), random.randint(20, 380), 0, "Cessna Citation Longitude", self.wpts) for i in range(2)]
        #self.planes = [Plane(200, 200, 0, "Cessna 152", self.wpts)]
        self.tower = Tower()
        self.ground = Ground()
        self.customBar = CustomisationBar()
        self.planeInfoPlane = None
        self.crashes = 0
        self.trafficSpawnTime = 40
        self.lastSpawnTime = time.time()
        self.arrivals = 0
        self.departures = 0
        
    def _initWpts(self):
        for y in range(9):
            for x in range(9):
                name = _genCallsign(5)
                while name in self.usedWptNames:
                    name = _genCallsign(5)

                self.usedWptNames.append(name)
                
                self.wpts[name] = (x*50-25, y*50)
        
        self.wpts["AIRPORT"] = (200, 200)

    def displayPlane(self, plane=None):
        if plane != None: self.planeInfoPlane = plane
        self.customBar.selectedPlane = self.planeInfoPlane
        self.customBar.selectedPlaneLbl = "Selected plane: " + self.planeInfoPlane.planeType
        self.customBar.selectedPlaneCallsign = 'Callsign: VH-' + self.planeInfoPlane.callsign
        self.customBar.selectedPlaneName = self.planeInfoPlane.planeType
        self.customBar.selectedPlaneSpeed = "Speed: " + str(int(self.planeInfoPlane.speed)) + 'kts'
        self.customBar.selectedPlaneHeading = "Heading: " + _formatNum(str(int(360-(self.planeInfoPlane.rotation+90)))) + "°"

    async def run(self):
        clock = pg.time.Clock()
        while True:
            self.screen.fill((0, 0, 0))
            #print(pg.mouse.get_pos())
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    exit()
                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    for plane in self.planes:
                        if abs(math.sqrt((pg.mouse.get_pos()[1]-plane.y-8)**2 + (pg.mouse.get_pos()[0]-plane.x)**2)) < 20: self.displayPlane(plane)
                    if pg.mouse.get_pos()[0] > self.customBar.speedUpButton.x and pg.mouse.get_pos()[0] < self.customBar.speedUpButton.x + self.customBar.speedUpButton.width and pg.mouse.get_pos()[1] > self.customBar.speedUpButton.y and pg.mouse.get_pos()[1] < self.customBar.speedUpButton.y + self.customBar.speedUpButton.height and self.customBar.selectedPlane != None and self.customBar.selectedPlane.tower == True:
                        if self.customBar.selectedPlane.speed != planeStats[self.customBar.selectedPlaneName]["stallspeed"] + 10: self.customBar.selectedPlane.speed = planeStats[self.customBar.selectedPlaneName]["maxspeed"]
                        else: self.customBar.selectedPlane.speed = planeStats[self.customBar.selectedPlaneName]["cruisespeed"]
                        self.customBar.speedUpButton.clicked = True
                    elif pg.mouse.get_pos()[0] > self.customBar.slowDownButton.x and pg.mouse.get_pos()[0] < self.customBar.slowDownButton.x + self.customBar.slowDownButton.width and pg.mouse.get_pos()[1] > self.customBar.slowDownButton.y and pg.mouse.get_pos()[1] < self.customBar.slowDownButton.y + self.customBar.slowDownButton.height and self.customBar.selectedPlane != None and self.customBar.selectedPlane.tower == True:
                        if self.customBar.selectedPlane.speed != planeStats[self.customBar.selectedPlaneName]["maxspeed"]: self.customBar.selectedPlane.speed = planeStats[self.customBar.selectedPlaneName]["stallspeed"] + 10
                        else: self.customBar.selectedPlane.speed = planeStats[self.customBar.selectedPlaneName]["cruisespeed"]
                        self.customBar.slowDownButton.clicked = True
                    elif pg.mouse.get_pos()[0] > self.customBar.taxiPauseButton.x and pg.mouse.get_pos()[0] < self.customBar.taxiPauseButton.x + self.customBar.taxiPauseButton.width and pg.mouse.get_pos()[1] > self.customBar.taxiPauseButton.y and pg.mouse.get_pos()[1] < self.customBar.taxiPauseButton.y + self.customBar.taxiPauseButton.height and self.customBar.selectedPlane != None and self.customBar.selectedPlane.tower == False:
                        if self.customBar.selectedPlane.paused == False and self.customBar.selectedPlane.speed < 21:
                            self.customBar.selectedPlane.paused = True
                            self.customBar.selectedPlane.speed = 0
                        elif self.customBar.selectedPlane.paused == True and self.customBar.selectedPlane.parked == False:
                            self.customBar.selectedPlane.paused = False
                            self.customBar.selectedPlane.speed = 20
                        self.customBar.taxiPauseButton.clicked = True
                    elif pg.mouse.get_pos()[0] > self.customBar.tkfGoAroundButton.x and pg.mouse.get_pos()[0] < self.customBar.tkfGoAroundButton.x + self.customBar.tkfGoAroundButton.width and pg.mouse.get_pos()[1] > self.customBar.tkfGoAroundButton.y and pg.mouse.get_pos()[1] < self.customBar.tkfGoAroundButton.y + self.customBar.tkfGoAroundButton.height and self.customBar.selectedPlane != None:
                        if self.customBar.selectedPlane.taxiIndex == 'hold' and not self.customBar.selectedPlane.rumbling:
                            self.customBar.selectedPlane.takeOff(True)
                            self.customBar.tkfGoAroundButton.clicked = True
                        if self.customBar.selectedPlane.tower == True and not self.customBar.selectedPlane.rumbling and abs(math.sqrt((200-self.customBar.selectedPlane.y)**2 + (200-self.customBar.selectedPlane.x)**2)) < 70 and self.customBar.selectedPlane.x > 200:
                            self.customBar.selectedPlane.goingAround = True
                            y = random.choice([3, 5])
                            self.customBar.selectedPlane.flightPath = [(3, 4), (3, y), (4, y), (5, y), (5, 4)]
                            self.customBar.tkfGoAroundButton.clicked = True
                elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                    if pg.mouse.get_pos()[0] > self.customBar.speedUpButton.x and pg.mouse.get_pos()[0] < self.customBar.speedUpButton.x + self.customBar.speedUpButton.width and pg.mouse.get_pos()[1] > self.customBar.speedUpButton.y and pg.mouse.get_pos()[1] < self.customBar.speedUpButton.y + self.customBar.speedUpButton.height: self.customBar.speedUpButton.clicked = False
                    elif pg.mouse.get_pos()[0] > self.customBar.slowDownButton.x and pg.mouse.get_pos()[0] < self.customBar.slowDownButton.x + self.customBar.slowDownButton.width and pg.mouse.get_pos()[1] > self.customBar.slowDownButton.y and pg.mouse.get_pos()[1] < self.customBar.slowDownButton.y + self.customBar.slowDownButton.height: self.customBar.slowDownButton.clicked = False
                    elif pg.mouse.get_pos()[0] > self.customBar.taxiPauseButton.x and pg.mouse.get_pos()[0] < self.customBar.taxiPauseButton.x + self.customBar.taxiPauseButton.width and pg.mouse.get_pos()[1] > self.customBar.taxiPauseButton.y and pg.mouse.get_pos()[1] < self.customBar.taxiPauseButton.y + self.customBar.taxiPauseButton.height: self.customBar.taxiPauseButton.clicked = False
                    elif pg.mouse.get_pos()[0] > self.customBar.tkfGoAroundButton.x and pg.mouse.get_pos()[0] < self.customBar.tkfGoAroundButton.x + self.customBar.tkfGoAroundButton.width and pg.mouse.get_pos()[1] > self.customBar.tkfGoAroundButton.y and pg.mouse.get_pos()[1] < self.customBar.tkfGoAroundButton.y + self.customBar.tkfGoAroundButton.height: self.customBar.tkfGoAroundButton.clicked = False

            if self.planeInfoPlane != None: self.displayPlane()

            pg.display.set_caption("ATC | fps: " + str(clock.get_fps()))

            if time.time() - self.lastSpawnTime > self.trafficSpawnTime:
                self.lastSpawnTime = time.time()
                self.trafficSpawnTime -= 1
                self.planes.append(Plane(random.randint(20, 380), random.randint(20, 380), 0, random.choice(list(planeStats.keys())), self.wpts))

            towerPlanes = []
            groundPlanes = []

            for plane in self.planes:
                if plane.tower == True: towerPlanes.append(plane)
                else: groundPlanes.append(plane)

            groundPlanes, crashes = self.ground.draw(self.screen, groundPlanes, pg.mouse.get_pos())
            self.crashes += crashes
            towerPlanes,  crashes, arrivals, departures = self.tower.draw(self.screen, towerPlanes, pg.mouse.get_pos())
            self.crashes += crashes
            self.arrivals += arrivals
            self.departures += departures

            self.planes = []

            self.planes.extend(towerPlanes)
            self.planes.extend(groundPlanes)

            self.customBar.crashes = "Crashes: " + str(self.crashes)
            self.customBar.arrivals = "Arrivals: " + str(self.arrivals)
            self.customBar.departures = "Departures: " + str(self.departures)
            self.customBar.trafficSpawnTime = "Next plane in: " + str(int(self.trafficSpawnTime - (time.time() - self.lastSpawnTime))) + "s"
            self.customBar.draw(self.screen)

            pg.draw.line(self.screen, (200, 200, 200), (400, 0), (400, 400), 2)

            pg.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)

window = None

async def run():
    global window
    window = Window()
    #cProfile.run('window.run()', sort='ncalls')
    await window.run()
if __name__ == "__main__":
    asyncio.run(run())