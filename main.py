import kivy
kivy.require("2.2.0")
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.graphics import (Color, Ellipse, Rectangle, Line, RoundedRectangle,
                            Canvas, Rotate, PushMatrix, PopMatrix, Translate)
from kivy.clock import Clock
from kivy.vector import Vector
import math, random, time

# ── Palette ─────────────────────────────────────────────────────────────────
def rgb(r,g,b,a=1): return r/255,g/255,b/255,a

PAL = dict(
    floor=(12/255,18/255,12/255),
    wall=(28/255,28/255,32/255),
    wall_face=(18/255,18/255,22/255),
    blood=(90/255,5/255,5/255),
    blood2=(130/255,10/255,8/255),
    hp_hi=rgb(0,195,65), hp_md=rgb(195,155,0), hp_lo=rgb(210,30,30),
    ammo=rgb(210,185,0), cyan=rgb(0,200,210), orange=rgb(255,140,20),
    pickup_hp=rgb(0,200,75), pickup_ammo=rgb(200,175,0), pickup_wpn=rgb(90,90,220),
    exit_glow=rgb(0,255,75),
    crawler=rgb(110,22,18), runner=rgb(55,12,12), brute=rgb(70,8,65),
    plyr=rgb(140,200,140), plyr_trim=rgb(80,140,80),
    hud_bg=rgb(3,9,3,0.88), hud_border=rgb(0,105,35),
    spark=rgb(255,215,80),
)

# ── Map ──────────────────────────────────────────────────────────────────────
TILE = 56
COLS, ROWS = 52, 36
_M = [[1]*COLS for _ in range(ROWS)]

def _rect(x,y,w,h):
    for r in range(y,y+h):
        for c in range(x,x+w):
            if 0<r<ROWS-1 and 0<c<COLS-1: _M[r][c]=0

def _hallH(x1,x2,y):
    for c in range(min(x1,x2),max(x1,x2)+2):
        for dy in range(3):
            r=y+dy
            if 0<r<ROWS-1 and 0<c<COLS-1: _M[r][c]=0

def _hallV(y1,y2,x):
    for r in range(min(y1,y2),max(y1,y2)+2):
        for dx in range(3):
            c=x+dx
            if 0<r<ROWS-1 and 0<c<COLS-1: _M[r][c]=0

ROOMS=[
    (2,2,10,8),(16,2,10,7),(30,2,10,8),(44,10,7,8),
    (30,16,10,8),(16,20,10,8),(3,20,10,8),(2,11,8,7),(20,10,8,8),
]
for rm in ROOMS: _rect(*rm)
_hallH(12,16,4); _hallH(26,30,4); _hallH(40,44,13)
_hallH(22,30,19); _hallH(13,16,22); _hallH(3,13,23)
_hallV(9,20,10);  _hallV(5,10,24); _hallV(8,16,35)
_hallH(28,35,19); _hallH(28,40,19); _hallV(10,18,20); _hallH(24,30,13)
for dr in range(3):
    for dc in range(3): _M[ROOMS[3][1]+2+dr][ROOMS[3][0]+2+dc]=2
MAP=_M

def wall(tc,tr):
    if tc<0 or tc>=COLS or tr<0 or tr>=ROWS: return True
    return MAP[tr][tc]==1

def tile_at(wx,wy):
    tc,tr=int(wx//TILE),int(wy//TILE)
    if tc<0 or tc>=COLS or tr<0 or tr>=ROWS: return 1
    return MAP[tr][tc]

# ── Weapons ──────────────────────────────────────────────────────────────────
WDATA={
    "pistol":  dict(name="PISTOL",  dmg=40, clip=12,res=48, rate=0.30,spread=0.04,shots=1,spd=16,rng=520),
    "shotgun": dict(name="SHOTGUN", dmg=28, clip=6, res=24, rate=0.88,spread=0.28,shots=7,spd=14,rng=300),
    "smg":     dict(name="SMG",     dmg=20, clip=30,res=150,rate=0.08,spread=0.11,shots=1,spd=18,rng=460),
}
WORDER=["pistol","shotgun","smg"]

# ── Entities ─────────────────────────────────────────────────────────────────
class Particle:
    __slots__= ('x','y','vx','vy','life','ml','r','col')
    def __init__(self,x,y,vx,vy,life,col,r=3):
        self.x=x;self.y=y;self.vx=vx;self.vy=vy;self.life=life;self.ml=life;self.r=r;self.col=col
    def update(self,dt):
        self.x+=self.vx*dt*60;self.y+=self.vy*dt*60
        self.vx*=0.87;self.vy*=0.87;self.life-=dt;return self.life>0

class Bullet:
    __slots__= ('x','y','vx','vy','life','dmg')
    def __init__(self,x,y,ang,spd,dmg,rng):
        self.x=x;self.y=y;self.vx=math.cos(ang)*spd;self.vy=math.sin(ang)*spd
        self.life=rng/spd;self.dmg=dmg
    def update(self,dt):
        s=dt*60;self.x+=self.vx*s;self.y+=self.vy*s;self.life-=dt
        if wall(int(self.x//TILE),int(self.y//TILE)): return False
        return self.life>0

class Enemy:
    def __init__(self,x,y,kind):
        self.x=float(x);self.y=float(y);self.kind=kind
        cfg={'crawler':dict(hp=85,spd=1.3,dmg=12,r=22,acd=1.0,det=380),
             'runner': dict(hp=38,spd=3.6,dmg=20,r=15,acd=0.5,det=500),
             'brute':  dict(hp=280,spd=0.72,dmg=38,r=34,acd=1.5,det=300)}[kind]
        for k,v in cfg.items(): setattr(self,k,v)
        self.max_hp=self.hp;self.angle=0.0;self.alive=True
        self.state='idle';self.idle_dir=random.uniform(0,math.pi*2);self.idle_t=1.5
        self.atk_t=0;self.flash_t=0;self.anim=random.uniform(0,6.28)

    def update(self,px,py,others,dt):
        self.anim+=dt*8
        if self.atk_t>0: self.atk_t-=dt
        if self.flash_t>0: self.flash_t-=dt
        dx=px-self.x;dy=py-self.y;dist=math.hypot(dx,dy)
        if dist<self.det: self.state='chase'
        elif dist>self.det*1.6: self.state='idle'
        if self.state=='chase':
            if dist>0:
                self.angle=math.atan2(dy,dx)
                self._move(math.cos(self.angle)*self.spd*dt*60,math.sin(self.angle)*self.spd*dt*60)
        else:
            self.idle_t-=dt
            if self.idle_t<=0: self.idle_dir=random.uniform(0,math.pi*2);self.idle_t=random.uniform(1.2,3.0)
            self._move(math.cos(self.idle_dir)*self.spd*0.28*dt*60,math.sin(self.idle_dir)*self.spd*0.28*dt*60)
        for o in others:
            if o is self or not o.alive: continue
            sx=self.x-o.x;sy=self.y-o.y;sd=math.hypot(sx,sy)
            if 0<sd<self.r+o.r+4: f=(self.r+o.r+4-sd)/sd*0.5;self.x+=sx*f;self.y+=sy*f

    def _move(self,dx,dy):
        m=self.r*0.82
        nx=self.x+dx
        if not wall(int((nx-m)//TILE),int((self.y-m)//TILE)) and \
           not wall(int((nx+m)//TILE),int((self.y-m)//TILE)) and \
           not wall(int((nx-m)//TILE),int((self.y+m)//TILE)) and \
           not wall(int((nx+m)//TILE),int((self.y+m)//TILE)): self.x=nx
        ny=self.y+dy
        if not wall(int((self.x-m)//TILE),int((ny-m)//TILE)) and \
           not wall(int((self.x+m)//TILE),int((ny-m)//TILE)) and \
           not wall(int((self.x-m)//TILE),int((ny+m)//TILE)) and \
           not wall(int((self.x+m)//TILE),int((ny+m)//TILE)): self.y=ny

    def hit(self,dmg):
        self.hp-=dmg;self.flash_t=0.18
        if self.hp<=0: self.alive=False

    def try_attack(self,px,py):
        if math.hypot(px-self.x,py-self.y)<self.r+20 and self.atk_t<=0:
            self.atk_t=self.acd;return self.dmg
        return 0

class Pickup:
    def __init__(self,x,y,kind,val=0,wname=None):
        self.x=x;self.y=y;self.kind=kind;self.val=val;self.wname=wname;self.alive=True;self.anim=random.uniform(0,6.28)

class Player:
    def __init__(self,x,y):
        self.x=float(x);self.y=float(y);self.angle=0.0;self.radius=16
        self.hp=100;self.max_hp=100;self.hit_t=0;self.step=0.0
        self.inv={w:dict(clip=WDATA[w]['clip'],res=WDATA[w]['res'],cd=0,reload_t=0) for w in WORDER}
        self.has_wpn={'pistol':True,'shotgun':False,'smg':False};self.cur_w=0;self.muzzle_t=0

    @property
    def wname(self): return WORDER[self.cur_w]
    @property
    def wd(self): return WDATA[self.wname]
    @property
    def wi(self): return self.inv[self.wname]

    def update(self,dx,dy,aim_ang,shooting,dt):
        if dx or dy:
            l=math.hypot(dx,dy)
            if l>0:
                dx/=l;dy/=l;spd=4.2
                m=self.radius*0.82;nx=self.x+dx*spd*dt*60
                if not wall(int((nx-m)//TILE),int((self.y-m)//TILE)) and \
                   not wall(int((nx+m)//TILE),int((self.y-m)//TILE)) and \
                   not wall(int((nx-m)//TILE),int((self.y+m)//TILE)) and \
                   not wall(int((nx+m)//TILE),int((self.y+m)//TILE)): self.x=nx
                ny=self.y+dy*spd*dt*60
                if not wall(int((self.x-m)//TILE),int((ny-m)//TILE)) and \
                   not wall(int((self.x+m)//TILE),int((ny-m)//TILE)) and \
                   not wall(int((self.x-m)//TILE),int((ny+m)//TILE)) and \
                   not wall(int((self.x+m)//TILE),int((ny+m)//TILE)): self.y=ny
                self.step+=dt*7
        self.angle=aim_ang
        if self.hit_t>0: self.hit_t-=dt
        if self.muzzle_t>0: self.muzzle_t-=dt
        wi=self.wi;wd=self.wd
        if wi['cd']>0: wi['cd']-=dt
        if wi['reload_t']>0:
            wi['reload_t']-=dt
            if wi['reload_t']<=0:
                need=wd['clip']-wi['clip'];give=min(need,wi['res'])
                wi['clip']+=give;wi['res']-=give

    def shoot(self):
        wi=self.wi;wd=self.wd
        if wi['reload_t']>0 or wi['cd']>0: return []
        if wi['clip']==0:
            if wi['res']>0: wi['reload_t']=1.2
            return []
        wi['clip']-=1;wi['cd']=wd['rate'];self.muzzle_t=0.15
        return [Bullet(self.x+math.cos(self.angle+(random.random()-0.5)*wd['spread'])*28,
                       self.y+math.sin(self.angle+(random.random()-0.5)*wd['spread'])*28,
                       self.angle+(random.random()-0.5)*wd['spread'],
                       wd['spd'],wd['dmg'],wd['rng']) for _ in range(wd['shots'])]

    def reload(self):
        wi=self.wi;wd=self.wd
        if wi['reload_t']<=0 and wi['res']>0 and wi['clip']<wd['clip']: wi['reload_t']=1.2

    def next_weapon(self):
        avail=[i for i,n in enumerate(WORDER) if self.has_wpn[n]]
        if not avail: return
        try: ci=avail.index(self.cur_w)
        except: ci=0
        self.cur_w=avail[(ci+1)%len(avail)]

# ── Game Widget ───────────────────────────────────────────────────────────────
class GameWidget(Widget):
    def __init__(self,**kw):
        super().__init__(**kw)
        self.state='menu';self.player=None;self.enemies=[];self.bullets=[]
        self.particles=[];self.pickups=[];self.kills=0;self.total_e=0
        self.cam_x=0.0;self.cam_y=0.0;self.shake=0.0;self.fr=0
        # Touch tracking
        self.joy_touch=None;self.joy_ox=0;self.joy_oy=0;self.joy_dx=0;self.joy_dy=0
        self.aim_touch=None;self.aim_angle=0.0;self.shooting=False
        self.joy_base=(0,0)
        Window.bind(on_resize=self._on_resize)
        Clock.schedule_interval(self._update,1/60)
        Clock.schedule_interval(self._draw,1/60)

    def _on_resize(self,*a): self._draw(0)

    def start(self):
        self.state='playing';self.fr=0;self.kills=0;self.particles=[];self.bullets=[];self.pickups=[]
        r0=ROOMS[0];px=(r0[0]+r0[2]//2)*TILE;py=(r0[1]+r0[3]//2)*TILE
        self.player=Player(px,py);self.aim_angle=0.0
        self.enemies=[]
        ecfg=[(1,'crawler',2),(1,'runner',1),(2,'crawler',2),(2,'runner',2),
              (3,'brute',1),(3,'runner',2),(4,'crawler',3),(4,'runner',1),
              (5,'crawler',2),(5,'brute',1),(6,'runner',3),(6,'crawler',2),
              (7,'crawler',2),(7,'runner',1),(8,'runner',2),(8,'crawler',2),(8,'brute',1)]
        rng=random.Random(42)
        for ridx,kind,n in ecfg:
            rm=ROOMS[ridx]
            for _ in range(n):
                self.enemies.append(Enemy((rm[0]+1+rng.random()*(rm[2]-2))*TILE,(rm[1]+1+rng.random()*(rm[3]-2))*TILE,kind))
        self.total_e=len(self.enemies)
        pcfg=[(2,'hp',30),(4,'ammo',15),(5,'hp',30),(6,'ammo',12),
              (7,'weapon',0,'shotgun'),(8,'weapon',0,'smg'),(1,'ammo',12),(3,'hp',30)]
        for pc in pcfg:
            ridx=pc[0];kind=pc[1];val=pc[2];wname=pc[3] if len(pc)>3 else None
            rm=ROOMS[ridx]
            self.pickups.append(Pickup((rm[0]+1+rng.random()*(rm[2]-3))*TILE+TILE//2,(rm[1]+1+rng.random()*(rm[3]-3))*TILE+TILE//2,kind,val,wname))
        self.cam_x=self.player.x-self.width/2;self.cam_y=self.player.y-self.height/2

    def _update(self,dt):
        dt=min(dt,0.05);self.fr+=1
        if self.state!='playing': return
        p=self.player
        # Update camera
        tx=p.x-self.width/2;ty=p.y-self.height/2
        self.cam_x+=(tx-self.cam_x)*0.12;self.cam_y+=(ty-self.cam_y)*0.12
        if self.shake>0: self.shake*=0.78
        # Player
        p.update(self.joy_dx,self.joy_dy,self.aim_angle,self.shooting,dt)
        if self.shooting:
            for b in p.shoot(): self.bullets.append(b)
        # Bullets
        nb=[]
        for b in self.bullets:
            if not b.update(dt):
                for _ in range(4):
                    self.particles.append(Particle(b.x,b.y,random.uniform(-2,2),random.uniform(-2,2),0.3,PAL['spark'],2))
                continue
            hit=False
            for e in self.enemies:
                if not e.alive: continue
                if (b.x-e.x)**2+(b.y-e.y)**2<(e.r+4)**2:
                    e.hit(b.dmg)
                    for _ in range(random.randint(8,16)):
                        a=random.uniform(0,6.28);s=random.uniform(2,6)
                        self.particles.append(Particle(b.x,b.y,math.cos(a)*s,math.sin(a)*s,random.uniform(0.25,0.55),PAL['blood'],random.randint(3,7)))
                    if not e.alive:
                        self.kills+=1
                        for _ in range(24):
                            a=random.uniform(0,6.28);s=random.uniform(1,9)
                            self.particles.append(Particle(e.x,e.y,math.cos(a)*s,math.sin(a)*s,random.uniform(0.4,0.9),PAL['blood'],random.randint(4,9)))
                        if random.random()<0.4:
                            self.pickups.append(Pickup(e.x,e.y,random.choice(['hp','ammo']),25))
                    hit=True;break
            if not hit: nb.append(b)
        self.bullets=nb
        # Enemies
        for e in self.enemies:
            if not e.alive: continue
            e.update(p.x,p.y,self.enemies,dt)
            dmg=e.try_attack(p.x,p.y)
            if dmg:
                p.hp-=dmg;p.hit_t=0.5;self.shake=9
                for _ in range(10):
                    a=random.uniform(0,6.28)
                    self.particles.append(Particle(p.x,p.y,math.cos(a)*3.5,math.sin(a)*3.5,0.4,PAL['hp_lo'],4))
                if p.hp<=0: p.hp=0;self.state='dead'
        self.particles=[pt for pt in self.particles if pt.update(dt)]
        # Pickups
        for pk in self.pickups:
            if not pk.alive: continue
            pk.anim+=dt*5
            if (p.x-pk.x)**2+(p.y-pk.y)**2<(p.radius+22)**2:
                pk.alive=False
                if pk.kind=='hp': p.hp=min(p.max_hp,p.hp+pk.val)
                elif pk.kind=='ammo':
                    wn=p.wname;p.inv[wn]['res']=min(WDATA[wn]['res'],p.inv[wn]['res']+pk.val)
                elif pk.kind=='weapon' and pk.wname:
                    p.has_wpn[pk.wname]=True;p.inv[pk.wname]['res']=WDATA[pk.wname]['res']
        if tile_at(p.x,p.y)==2: self.state='win'

    def _draw(self,dt):
        W=self.width;H=self.height
        if W<=0 or H<=0: return
        ox=int(self.cam_x);oy=int(self.cam_y)
        sk=0
        if self.shake>0: sk=int(self.shake*0.5);ox+=random.randint(-sk,sk);oy+=random.randint(-sk,sk)
        self.canvas.clear()
        with self.canvas:
            if self.state in ('playing','dead','win'):
                self._draw_world(ox,oy,W,H)
                self._draw_particles(ox,oy)
                self._draw_enemies(ox,oy)
                self._draw_player(ox,oy)
                self._draw_bullets(ox,oy)
                self._draw_fog(ox,oy,W,H)
                self._draw_hud(W,H)
                if self.state=='dead': self._draw_overlay("YOU DIED",f"Kills: {self.kills}/{self.total_e}","TAP TO RETRY",(0.85,0.12,0.12,1),W,H)
                elif self.state=='win': self._draw_overlay("ESCAPED!",f"Kills: {self.kills}/{self.total_e}","TAP TO PLAY AGAIN",(0,0.87,0.3,1),W,H)
            elif self.state=='menu': self._draw_menu(W,H)
            self._draw_joystick(W,H)

    def _draw_world(self,ox,oy,W,H):
        c0=max(0,ox//TILE-1);c1=min(COLS-1,(ox+W)//TILE+2)
        r0=max(0,oy//TILE-1);r1=min(ROWS-1,(oy+H)//TILE+2)
        for r in range(r0,r1+1):
            for c in range(c0,c1+1):
                tx=c*TILE-ox;ty=r*TILE-oy;tile=MAP[r][c]
                rng2=random.Random(r*1000+c)
                if tile==1:
                    Color(0.11,0.11,0.13,1);Rectangle(pos=(tx,ty),size=(TILE,TILE))
                    for _ in range(6):
                        gx=rng2.randint(0,TILE-4);gy=rng2.randint(0,TILE-4);gs=rng2.randint(2,6)
                        v=rng2.randint(-10,10)/255.0
                        Color(0.13+v,0.13+v,0.15+v,1);Rectangle(pos=(tx+gx,ty+gy),size=(gs,gs))
                    Color(0.07,0.07,0.09,1)
                    Rectangle(pos=(tx,ty),size=(TILE,1));Rectangle(pos=(tx,ty),size=(1,TILE))
                    if r+1<ROWS and MAP[r+1][c]!=1:
                        Color(0.08,0.08,0.10,1);Rectangle(pos=(tx,ty+TILE-4),size=(TILE,4))
                elif tile in (0,2):
                    v=((r*31+c*17)%9)/9.0*0.025
                    Color(0.047+v,0.072+v,0.047+v,1);Rectangle(pos=(tx,ty),size=(TILE,TILE))
                    Color(0.035,0.055,0.035,1)
                    Rectangle(pos=(tx,ty),size=(TILE,1));Rectangle(pos=(tx,ty),size=(1,TILE))
                    if tile==2:
                        p2=0.35+0.35*math.sin(self.fr*0.07)
                        Color(0,p2*0.63,0,p2*0.22);Rectangle(pos=(tx,ty),size=(TILE,TILE))
                        Color(0,0.85*p2,0.15,0.8*p2)
                        Line(rectangle=(tx+3,ty+3,TILE-6,TILE-6),width=2)
        # Pickups
        for pk in self.pickups:
            if not pk.alive: continue
            sx=pk.x-ox;sy=pk.y-oy;bob=math.sin(pk.anim)*4;sy+=bob;p2=0.5+0.5*math.sin(pk.anim*1.4)
            if pk.kind=='hp':
                Color(0,0.78,0.29,1);Ellipse(pos=(sx-13,sy-13),size=(26,26))
                Color(0,1,0.4,p2*0.8);Line(circle=(sx,sy,14),width=1.5)
                Color(1,1,1,1);Rectangle(pos=(sx-2,sy-8),size=(4,16));Rectangle(pos=(sx-8,sy-2),size=(16,4))
            elif pk.kind=='ammo':
                Color(0.78,0.68,0,1);Ellipse(pos=(sx-12,sy-12),size=(24,24))
                Color(1,0.87,0.2,p2*0.8);Line(circle=(sx,sy,13),width=1.5)
            elif pk.kind=='weapon':
                Color(0.35,0.35,0.86,1);Ellipse(pos=(sx-14,sy-14),size=(28,28))
                Color(0.58,0.58,1,p2*0.8);Line(circle=(sx,sy,15),width=2)

    def _draw_particles(self,ox,oy):
        for pt in self.particles:
            a=min(1,pt.life/pt.ml)
            Color(pt.col[0],pt.col[1],pt.col[2],a*0.9)
            r=max(1,pt.r*a)
            Ellipse(pos=(pt.x-ox-r,pt.y-oy-r),size=(r*2,r*2))

    def _draw_enemies(self,ox,oy):
        for e in self.enemies:
            if not e.alive: continue
            sx=e.x-ox;sy=e.y-oy;r=e.r;fl=e.flash_t>0
            # Shadow
            Color(0,0,0,0.35);Ellipse(pos=(sx-r*1.2+3,sy-r*0.5),size=(r*2.4,r))
            # Limbs
            nlimbs={'crawler':6,'runner':4,'brute':8}[e.kind]
            for i in range(nlimbs):
                la=e.angle+math.pi+(i/nlimbs)*math.pi*2+math.sin(e.anim+i)*0.55
                llen=r*1.15 if e.kind!='brute' else r*1.4
                lw=2 if e.kind=='runner' else 3 if e.kind=='crawler' else 5
                ex2=sx+math.cos(la)*llen;ey2=sy+math.sin(la)*llen
                if e.kind=='crawler': Color(0.35,0.06,0.04,1)
                elif e.kind=='runner': Color(0.18,0.04,0.04,1)
                else: Color(0.22,0.03,0.22,1)
                Line(points=[sx,sy,ex2,ey2],width=lw)
                Ellipse(pos=(ex2-lw,ey2-lw),size=(lw*2,lw*2))
            # Body
            Color(0,0,0,1);Ellipse(pos=(sx-r+2,sy-r+2),size=(r*2,r*2))
            if e.kind=='crawler': bc=(0.43,0.08,0.07,1);ic=(0.27,0.05,0.04,1)
            elif e.kind=='runner': bc=(0.22,0.05,0.05,1);ic=(0.14,0.03,0.03,1)
            else: bc=(0.28,0.03,0.25,1);ic=(0.18,0.02,0.16,1)
            if fl: bc=(1,0.31,0.24,1);ic=(0.7,0.15,0.1,1)
            Color(*bc);Ellipse(pos=(sx-r,sy-r),size=(r*2,r*2))
            Color(*ic);Ellipse(pos=(sx-r*0.55,sy-r*0.55),size=(r*1.1,r*1.1))
            # Highlight
            Color(min(1,bc[0]+0.15),min(1,bc[1]+0.1),min(1,bc[2]+0.1),0.6)
            Ellipse(pos=(sx-r*0.65,sy+r*0.1),size=(r*0.6,r*0.4))
            # Eyes
            n_eyes=3 if e.kind=='brute' else 2
            for i in range(n_eyes):
                ea=e.angle+(i-(n_eyes-1)/2)*0.42
                dist_e=r*0.48
                ex3=sx+math.cos(ea)*dist_e;ey3=sy+math.sin(ea)*dist_e
                er=5 if e.kind=='brute' else 4
                Color(0.08,0,0,1);Ellipse(pos=(ex3-er,ey3-er),size=(er*2,er*2))
                if e.kind=='brute': Color(0.82,0,1,1)
                else: Color(1,0.14,0.14,1)
                er2=er-1.5;Ellipse(pos=(ex3-er2,ey3-er2),size=(er2*2,er2*2))
                Color(1,1,1,0.8);Ellipse(pos=(ex3-1,ey3-1),size=(2,2))
            # HP bar
            if e.hp<e.max_hp:
                bw=r*2.5;bx2=sx-bw/2;by2=sy+r+5
                Color(0.12,0,0,1);Rectangle(pos=(bx2,by2),size=(bw,6))
                pct=max(0,e.hp/e.max_hp)
                hc=(0,0.7,0.24,1) if pct>0.5 else (0.7,0.55,0,1) if pct>0.25 else (0.78,0.08,0.08,1)
                Color(*hc);Rectangle(pos=(bx2,by2),size=(bw*pct,6))
                Color(0.24,0.24,0.24,1);Line(rectangle=(bx2,by2,bw,6),width=1)

    def _draw_player(self,ox,oy):
        p=self.player
        sx=p.x-ox;sy=p.y-oy;r=p.radius;a=p.angle
        Color(0,0,0,0.38);Ellipse(pos=(sx-r*1.2+3,sy-r*0.5-2),size=(r*2.4,r))
        for side,off in [(-1,0),(1,math.pi)]:
            la=a+math.pi+math.sin(p.step+side*0.9)*0.55+off*0.3
            lx=sx+math.cos(la)*(r*0.8);ly=sy+math.sin(la)*(r*0.8)
            Color(0.2,0.39,0.2,1);Line(points=[sx,sy,lx,ly],width=7)
            Ellipse(pos=(lx-4,ly-4),size=(8,8))
        hit=p.hit_t>0
        Color(0,0,0,1);Ellipse(pos=(sx-r+2,sy-r+2),size=(r*2,r*2))
        Color(*((0.9,0.35,0.35,1) if hit else PAL['plyr_trim']));Ellipse(pos=(sx-r,sy-r),size=(r*2,r*2))
        Color(*((0.7,0.2,0.2,1) if hit else PAL['plyr']));Ellipse(pos=(sx-r+2,sy-r+2),size=((r-2)*2,(r-2)*2))
        Color(0.2,0.39,0.2,1);Ellipse(pos=(sx-r*0.5,sy-r*0.5),size=(r,r))
        Color(0.55,0.78,0.55,0.55);Ellipse(pos=(sx-r*0.65,sy+r*0.1),size=(r*0.55,r*0.38))
        # Gun
        gl=30;gsx=sx+math.cos(a)*22;gsy=sy+math.sin(a)*22
        gex=gsx+math.cos(a)*gl;gey=gsy+math.sin(a)*gl
        Color(0,0,0,1);Line(points=[sx+math.cos(a)*8,sy+math.sin(a)*8,gex,gey],width=9)
        Color(0.22,0.22,0.23,1);Line(points=[sx+math.cos(a)*9,sy+math.sin(a)*9,gex,gey],width=7)
        Color(0.35,0.35,0.37,1);Line(points=[sx+math.cos(a)*11,sy+math.sin(a)*11,gex-math.cos(a)*3,gey-math.sin(a)*3],width=3)
        if p.muzzle_t>0:
            frac=p.muzzle_t/0.15
            fx=gex+math.cos(a)*6;fy=gey+math.sin(a)*6
            for sz,al in [(28,0.22),(18,0.45),(10,0.75),(5,1)]:
                Color(1,0.87,0.4,al*frac);Ellipse(pos=(fx-sz,fy-sz),size=(sz*2,sz*2))

    def _draw_bullets(self,ox,oy):
        for b in self.bullets:
            Color(1,0.9,0.3,1);Ellipse(pos=(b.x-ox-3,b.y-oy-3),size=(6,6))
            Color(1,1,1,0.9);Ellipse(pos=(b.x-ox-1.5,b.y-oy-1.5),size=(3,3))

    def _draw_fog(self,ox,oy,W,H):
        p=self.player
        if not p: return
        sx=p.x-ox;sy=p.y-oy;a=p.angle
        # Dark overlay everywhere
        Color(0,0,0,0.94);Rectangle(pos=(0,0),size=(W,H))
        # Punch out ambient glow
        for rad,al in [(90,0.92),(70,0.88),(50,0.82),(32,0.7),(18,0.5),(8,0.2)]:
            Color(0,0,0,1-al);Ellipse(pos=(sx-rad,sy-rad),size=(rad*2,rad*2))
        # Flashlight (simplified polygon as line fan)
        half=math.pi/4.5;step2=math.pi*2*half/80;max_d=480
        Color(1,0.95,0.85,0.88)
        pts=[]
        for i in range(81):
            ang=a-half+i*(half*2/80)
            for d in range(8,max_d,8):
                wx=p.x+math.cos(ang)*d;wy=p.y+math.sin(ang)*d
                if wall(int(wx//TILE),int(wy//TILE)): break
            pts.extend([sx+math.cos(ang)*(d-8),sy+math.sin(ang)*(d-8)])
        if len(pts)>=4:
            Color(0,0,0,0);Line(points=[sx,sy]+pts+[sx,sy],width=1)
        # Re-draw cone slightly transparent
        cone_pts=[sx,sy]+pts+[sx,sy]
        # Damage / low-hp effects
        if p.hit_t>0:
            Color(0.75,0,0,0.45*(p.hit_t/0.5));Rectangle(pos=(0,0),size=(W,H))
        if p.hp<30:
            pulse=0.22+0.18*math.sin(self.fr*0.2)
            Color(0.63,0,0,pulse);Rectangle(pos=(0,0),size=(W,H))

    def _draw_hud(self,W,H):
        p=self.player
        if not p: return
        HH=110;HY=0;pad=14
        Color(*PAL['hud_bg']);Rectangle(pos=(0,HY),size=(W,HH))
        Color(*PAL['hud_border'],0.9);Line(points=[0,HY+HH,W,HY+HH],width=1)
        # HP bar
        BW=min(260,W*0.28);BX=pad;BY=HY+HH-30
        pct=max(0,p.hp/p.max_hp)
        hc=PAL['hp_hi'] if pct>0.5 else PAL['hp_md'] if pct>0.25 else PAL['hp_lo']
        Color(0.07,0,0,1);Rectangle(pos=(BX,BY),size=(BW,18))
        Color(*hc);Rectangle(pos=(BX,BY),size=(BW*pct,18))
        for i in range(1,10): mx=BX+BW*i//10;Color(0,0.16,0.06,1);Line(points=[mx,BY,mx,BY+18],width=1)
        Color(0,0.41,0.13,0.7);Line(rectangle=(BX,BY,BW,18),width=1)
        Color(0.31,0.78,0.31,1)
        # Weapon slots
        avail=[n for n in WORDER if p.has_wpn[n]]
        sw_w=min(180,W*0.18);sw_gap=8;sw_start=BX
        BY2=HY+HH-80
        for i,wn in enumerate(WORDER):
            wd=WDATA[wn];wi=p.inv[wn];has=p.has_wpn[wn];active=(p.cur_w==i)
            sx2=sw_start+i*(sw_w+sw_gap);sy2=BY2
            if active: Color(0.04,0.14,0.04,1)
            else: Color(0.02,0.06,0.02,1)
            RoundedRectangle(pos=(sx2,sy2),size=(sw_w,34),radius=[6])
            bc=(0,0.45,0.14,1) if active else (0,0.17,0.06,1)
            Color(*bc);Line(rounded_rectangle=(sx2,sy2,sw_w,34,6),width=1.5 if active else 1)
            if not has:
                Color(0.22,0.22,0.22,1)
            else:
                if wi['reload_t']>0:
                    rp=1-wi['reload_t']/1.2
                    Color(0.78,0.68,0,1)
                    Rectangle(pos=(sx2+5,sy2+4),size=((sw_w-10)*rp,4))
                    Color(0.6,0.5,0,1)
                else:
                    clip_c=(0.82,0.72,0,1) if wi['clip']>0 else (0.78,0.12,0.12,1)
                    Color(*clip_c)
                    Rectangle(pos=(sx2+5,sy2+4),size=((sw_w-10)*(wi['clip']/wd['clip']),4))
        # Right side: kills + weapon name
        wd=WDATA[p.wname];wi=p.inv[p.wname]
        rtext_x=W-pad-160
        Color(0.51,0.35,0.35,1)
        Color(*PAL['hud_border'])
        # Reload button label
        if wi['reload_t']>0:
            Color(0.78,0.68,0,1)
        # Weapon name top right
        Color(0,0.82,0.29,1)

    def _draw_overlay(self,title,sub,hint,tcol,W,H):
        Color(0,0,0,0.58);Rectangle(pos=(0,0),size=(W,H))
        bw=min(580,W-40);bh=200;bx=(W-bw)/2;by=(H-bh)/2
        Color(0.01,0.04,0.01,0.97);RoundedRectangle(pos=(bx,by),size=(bw,bh),radius=[12])
        Color(0,0.31,0.11,1);Line(rounded_rectangle=(bx,by,bw,bh,12),width=1.5)
        Color(*tcol)
        Color(*PAL['exit_glow'])
        pulse=0.5+0.5*math.sin(self.fr*0.12)
        Color(0,0.35+0.35*pulse,0.12+0.12*pulse,1)

    def _draw_menu(self,W,H):
        Color(0.004,0.016,0.004,1);Rectangle(pos=(0,0),size=(W,H))
        for x in range(0,int(W),72):
            Color(0,0.07,0.024,1);Line(points=[x,0,x,H],width=1)
        for y in range(0,int(H),72):
            Color(0,0.07,0.024,1);Line(points=[0,y,W,y],width=1)
        # Vignette
        for i in range(6):
            r2=min(W,H)*(0.35+i*0.15);a=i*0.045
            Color(0,0,0,a);Ellipse(pos=(W/2-r2,H/2-r2),size=(r2*2,r2*2))
        # Glowing title cross
        pulse=0.5+0.5*math.sin(self.fr*0.04)
        Color(0,0.4+0.4*pulse,0.08+0.08*pulse,0.6)
        Line(points=[W/2,H*0.05,W/2,H*0.95],width=1)
        Line(points=[0,H/2,W,H/2],width=1)
        # Title blocks
        Color(0,0.78+0.2*pulse,0.15+0.1*pulse,1)
        Rectangle(pos=(W/2-120,H*0.52),size=(240,12))
        Color(0.82+0.15*pulse,0.08,0.08,1)
        Rectangle(pos=(W/2-120,H*0.48-12),size=(240,12))
        pulse2=0.5+0.5*math.sin(self.fr*0.07)
        Color(0,0.55+0.35*pulse2,0.12,0.8)
        Rectangle(pos=(W/2-60,H*0.38),size=(120,8))

    def _draw_joystick(self,W,H):
        if self.state!='playing': return
        # Left joystick base
        jbx=self.joy_base[0];jby=self.joy_base[1]
        JR=70
        Color(0,0.22,0.07,0.25);Ellipse(pos=(jbx-JR,jby-JR),size=(JR*2,JR*2))
        Color(0,0.5,0.17,0.4);Line(circle=(jbx,jby,JR),width=2)
        # Knob
        kx=jbx+self.joy_dx*JR;ky=jby+self.joy_dy*JR
        Color(0,0.6,0.2,0.7);Ellipse(pos=(kx-22,ky-22),size=(44,44))
        Color(0,0.9,0.3,0.9);Line(circle=(kx,ky,22),width=2)
        # Shoot button (right side)
        bx2=W-80;by2=H/2
        p=self.player
        if p:
            ammo_ok=p.inv[p.wname]['clip']>0 or p.inv[p.wname]['reload_t']>0
            if self.shooting: Color(0.9,0.1,0.1,0.7)
            elif not ammo_ok: Color(0.5,0.1,0.1,0.4)
            else: Color(0.1,0.5,0.15,0.5)
        else: Color(0.1,0.4,0.15,0.45)
        Ellipse(pos=(bx2-45,by2-45),size=(90,90))
        Color(1,1,1,0.7);Line(circle=(bx2,by2,45),width=2)
        # Weapon switch button
        Color(0.1,0.2,0.55,0.5);Ellipse(pos=(bx2-45,by2+70),size=(55,55))
        Color(0.4,0.4,1,0.8);Line(circle=(bx2-17,by2+97),width=1.5,width_px=True)
        # Reload button
        if p and p.inv[p.wname]['clip']<WDATA[p.wname]['clip'] and p.inv[p.wname]['res']>0:
            Color(0.5,0.4,0,0.55);Ellipse(pos=(bx2-105,by2-25),size=(50,50))
            Color(0.9,0.75,0,0.9);Line(circle=(bx2-80,by2),width=1.5,width_px=True)

    # ── Touch handling ────────────────────────────────────────────────────────
    def on_touch_down(self,touch):
        W=self.width;H=self.height
        if self.state=='menu': self.start(); return True
        if self.state in ('dead','win'): self.state='menu'; return True
        if self.state!='playing': return True
        tx=touch.x;ty=touch.y
        JR=70;JZ=200  # left zone width
        bx_shoot=W-80;by_shoot=H/2
        bx_sw=W-80;by_sw=H/2+97
        bx_rl=W-80;by_rl=H/2

        # Shoot button check
        if math.hypot(tx-bx_shoot,ty-by_shoot)<50:
            self.shooting=True; return True
        # Switch weapon
        if math.hypot(tx-bx_sw,ty-by_sw)<32:
            if self.player: self.player.next_weapon(); return True
        # Reload
        if math.hypot(tx-(bx_rl-80),ty-by_rl)<30:
            if self.player: self.player.reload(); return True

        if tx<JZ:  # left joystick
            self.joy_touch=touch.id;self.joy_ox=tx;self.joy_oy=ty;self.joy_base=(tx,ty);self.joy_dx=0;self.joy_dy=0
        else:  # right aim area
            self.aim_touch=touch.id
            if self.player: self.aim_angle=math.atan2(ty-H/2,tx-W/2)
        return True

    def on_touch_move(self,touch):
        if self.state!='playing': return True
        W=self.width;H=self.height;JR=70
        if hasattr(touch,'id') and touch.id==self.joy_touch:
            dx=touch.x-self.joy_ox;dy=touch.y-self.joy_oy
            dist=math.hypot(dx,dy)
            if dist>JR: dx=dx/dist;dy=dy/dist
            else: dx/=JR;dy/=JR
            self.joy_dx=dx;self.joy_dy=dy
        elif hasattr(touch,'id') and touch.id==self.aim_touch:
            if self.player:
                p=self.player;sx=p.x-self.cam_x;sy=p.y-self.cam_y
                self.aim_angle=math.atan2(touch.y-sy,touch.x-sx)
        return True

    def on_touch_up(self,touch):
        if hasattr(touch,'id'):
            if touch.id==self.joy_touch: self.joy_touch=None;self.joy_dx=0;self.joy_dy=0;self.joy_base=(0,0)
            if touch.id==self.aim_touch: self.aim_touch=None;self.shooting=False
        self.shooting=False
        return True

class ParasiteApp(App):
    def build(self):
        Window.clearcolor=(0,0,0,1)
        return GameWidget()

if __name__=='__main__':
    ParasiteApp().run()
