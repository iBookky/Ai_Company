/* ═══════════════════════════════════════════════════════════════
   office3d.js — Interactive 3D Virtual AI Enterprise Office
   Three.js Isometric Workspace & Autonomous AI Agent Life
   One-Person AI Enterprise
   ═══════════════════════════════════════════════════════════════ */

'use strict';

let _officeScene = null;
let _officeCamera = null;
let _officeRenderer = null;
let _officeControls = null;
let _officeAnimId = null;
let _officeIsInitialized = false;

// Raycasting & Interaction
let _officeRaycaster = null;
let _officeMouse = null;
let _officeHoveredAgent = null;
let _officeSelectedAgentId = null;
let _officeCameraTarget = { pos: null, lookAt: null, active: false };

// Agents & World Objects
const _officeEmployees = {};
let _officeClickableObjects = [];
let _officeSyncInterval = null;

// Preset Camera Positions
const OFFICE_CAMERA_PRESETS = {
  isometric: { pos: [22, 20, 22], target: [0, 1, 0] },
  top:       { pos: [0, 32, 0.5], target: [0, 0, 0] },
  boardroom: { pos: [0, 8, 8], target: [0, 1, 0] },
  lounge:    { pos: [0, 7, -5], target: [0, 1, -10] },
};

// 6 AI Employees Master Specification
const OFFICE_EMPLOYEE_DEFS = {
  '01_secretary': {
    id: '01_secretary',
    name: 'อิงฟ้า',
    role: 'Executive Secretary & CKO',
    dept: 'สำนักเลขาธิการ & CKO',
    color: 0x38bdf8,
    shirtColor: 0x0284c7,
    pantsColor: 0x1e293b,
    deskPos: [-8, 0, -6],
    deskRot: Math.PI * 0.25,
    chairPos: [-8, 0, -6.8],
    avatarUrl: '/static/img/avatars/01_secretary.jpg',
    defaultThought: 'วางแผนกลยุทธ์และจัดสรรงานให้ทุกแผนก',
  },
  '03_developer': {
    id: '03_developer',
    name: 'บิ๊นท์',
    role: 'Lead Full-Stack Developer',
    dept: 'ฝ่ายพัฒนาระบบซอฟต์แวร์',
    color: 0x818cf8,
    shirtColor: 0x4f46e5,
    pantsColor: 0x0f172a,
    deskPos: [8, 0, -6],
    deskRot: -Math.PI * 0.25,
    chairPos: [8, 0, -6.8],
    avatarUrl: '/static/img/avatars/03_developer.jpg',
    defaultThought: 'ออกแบบสถาปัตยกรรม Backend & API',
  },
  '02_การตลาด_ai': {
    id: '02_การตลาด_ai',
    name: 'ลิซ่า',
    role: 'Head of Marketing & Social Content',
    dept: 'ฝ่ายการตลาด & Social Content',
    color: 0xf472b6,
    shirtColor: 0xdb2777,
    pantsColor: 0x334155,
    deskPos: [8, 0, 6],
    deskRot: -Math.PI * 0.75,
    chairPos: [8, 0, 6.8],
    avatarUrl: '/static/img/avatars/02_marketing.jpg',
    defaultThought: 'คิดสคริปต์ไวรัล TikTok & แคมเปญโปรโมต',
  },
  '04_data_analyst': {
    id: '04_data_analyst',
    name: 'มุก',
    role: 'Senior QA & Data Analyst',
    dept: 'ฝ่ายตรวจสอบคุณภาพ & Data',
    color: 0x34d399,
    shirtColor: 0x059669,
    pantsColor: 0x1e293b,
    deskPos: [-8, 0, 6],
    deskRot: Math.PI * 0.75,
    chairPos: [-8, 0, 6.8],
    avatarUrl: '/static/img/avatars/04_data_analyst.jpg',
    defaultThought: 'ตรวจสอบ Code Review และ Funnel Conversion',
  },
  '05_accounting': {
    id: '05_accounting',
    name: 'พลอย',
    role: 'Finance & Cloud Cost Controller',
    dept: 'ฝ่ายการเงิน & ต้นทุน Cloud',
    color: 0xa78bfa,
    shirtColor: 0x7c3aed,
    pantsColor: 0x0f172a,
    deskPos: [-12, 0, 0],
    deskRot: Math.PI * 0.5,
    chairPos: [-12.8, 0, 0],
    avatarUrl: '/static/img/avatars/05_accounting.jpg',
    defaultThought: 'ควบคุมงบประมาณ API Token และจุดคุ้มทุน ROI',
  },
  '06_devops': {
    id: '06_devops',
    name: 'ก้อง',
    role: 'Cloud DevOps & Infra Specialist',
    dept: 'ฝ่ายวิศวกรรมคลาวด์ & DevOps',
    color: 0xfbbf24,
    shirtColor: 0xd97706,
    pantsColor: 0x1e293b,
    deskPos: [12, 0, 0],
    deskRot: -Math.PI * 0.5,
    chairPos: [12.8, 0, 0],
    avatarUrl: '/static/img/avatars/06_devops.jpg',
    defaultThought: 'เฝ้าระวังเซิร์ฟเวอร์ Uptime 99.99% & CI/CD',
  },
};

// Common Points of Interest for Wandering
const OFFICE_WAYPOINTS = [
  { name: 'boardroom_1', pos: [-2, 0, -1] },
  { name: 'boardroom_2', pos: [2, 0, -1] },
  { name: 'boardroom_3', pos: [-2, 0, 1] },
  { name: 'boardroom_4', pos: [2, 0, 1] },
  { name: 'coffee_machine', pos: [-1.5, 0, -9] },
  { name: 'water_cooler', pos: [1.5, 0, -9] },
  { name: 'sofa_lounge', pos: [0, 0, -11] },
  { name: 'presentation_stage', pos: [0, 0, 9] },
  { name: 'center_hall', pos: [0, 0, 3] },
];

// ═══════════════════════════════════════════════════════════════
//  1. INITIALIZATION & LIFECYCLE
// ═══════════════════════════════════════════════════════════════

function initOffice3D() {
  const container = document.getElementById('office3d-canvas-container');
  if (!container) return;

  if (_officeIsInitialized) {
    onOfficeWindowResize();
    syncOfficeWithSimState();
    return;
  }

  // 1. Scene
  _officeScene = new THREE.Scene();
  _officeScene.background = new THREE.Color(0x0a0e17);
  _officeScene.fog = new THREE.FogExp2(0x0a0e17, 0.015);

  // 2. Camera (Perspective with isometric feel)
  const width = container.clientWidth || 1000;
  const height = container.clientHeight || 700;
  _officeCamera = new THREE.PerspectiveCamera(40, width / height, 0.1, 200);
  _officeCamera.position.set(22, 20, 22);

  // 3. Renderer
  _officeRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
  _officeRenderer.setSize(width, height);
  _officeRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  _officeRenderer.shadowMap.enabled = true;
  _officeRenderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.innerHTML = '';
  container.appendChild(_officeRenderer.domElement);

  // 4. Controls
  if (typeof THREE.OrbitControls !== 'undefined') {
    _officeControls = new THREE.OrbitControls(_officeCamera, _officeRenderer.domElement);
    _officeControls.enableDamping = true;
    _officeControls.dampingFactor = 0.05;
    _officeControls.maxPolarAngle = Math.PI / 2 - 0.05; // Don't go below floor
    _officeControls.minDistance = 6;
    _officeControls.maxDistance = 60;
    _officeControls.target.set(0, 1, 0);
  }

  // 5. Lighting
  setupOfficeLighting();

  // 6. Architecture & Environment
  buildOfficeArchitecture();

  // 7. 6 AI Employees
  buildOfficeEmployees();

  // 8. Render HUD chips
  renderOfficeHudChips();

  // 9. Interaction Setup
  _officeRaycaster = new THREE.Raycaster();
  _officeMouse = new THREE.Vector2();
  container.addEventListener('mousemove', onOfficeMouseMove);
  container.addEventListener('click', onOfficeCanvasClick);
  window.addEventListener('resize', onOfficeWindowResize);

  // 10. Start Animation Loop
  _officeIsInitialized = true;
  animateOffice();

  // 11. Initial State Sync
  syncOfficeWithSimState();
  if (_officeSyncInterval) clearInterval(_officeSyncInterval);
  _officeSyncInterval = setInterval(syncOfficeWithSimState, 2000);
}

// ═══════════════════════════════════════════════════════════════
//  2. LIGHTING & ENVIRONMENT
// ═══════════════════════════════════════════════════════════════

function setupOfficeLighting() {
  // Ambient Light
  const ambient = new THREE.AmbientLight(0xffffff, 0.45);
  _officeScene.add(ambient);

  // Directional Sun Light
  const sunLight = new THREE.DirectionalLight(0xffffff, 0.85);
  sunLight.position.set(20, 30, 15);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.width = 2048;
  sunLight.shadow.mapSize.height = 2048;
  sunLight.shadow.camera.near = 5;
  sunLight.shadow.camera.far = 70;
  const d = 25;
  sunLight.shadow.camera.left = -d;
  sunLight.shadow.camera.right = d;
  sunLight.shadow.camera.top = d;
  sunLight.shadow.camera.bottom = -d;
  sunLight.shadow.bias = -0.0005;
  _officeScene.add(sunLight);

  // Cyber Neon Accent Point Lights at Key Pods
  const colors = [0x6366f1, 0x38bdf8, 0x10b981, 0xf472b6];
  const positions = [[-8, 3, -6], [8, 3, -6], [8, 3, 6], [-8, 3, 6]];
  positions.forEach((pos, idx) => {
    const light = new THREE.PointLight(colors[idx % colors.length], 0.65, 14);
    light.position.set(pos[0], pos[1], pos[2]);
    _officeScene.add(light);
  });

  // Central Boardroom Spotlight
  const centerLight = new THREE.SpotLight(0xffffff, 0.8, 20, Math.PI / 4, 0.3);
  centerLight.position.set(0, 12, 0);
  centerLight.target.position.set(0, 0, 0);
  _officeScene.add(centerLight);
  _officeScene.add(centerLight.target);
}

// ═══════════════════════════════════════════════════════════════
//  3. ARCHITECTURE, DESKS & FURNITURE
// ═══════════════════════════════════════════════════════════════

function buildOfficeArchitecture() {
  const materials = {
    floor: new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.25,
      metalness: 0.1,
    }),
    gridLines: new THREE.LineBasicMaterial({ color: 0x1e293b, transparent: true, opacity: 0.5 }),
    wallGlass: new THREE.MeshPhysicalMaterial({
      color: 0x1e1b4b,
      transparent: true,
      opacity: 0.35,
      roughness: 0.1,
      transmission: 0.8,
      thickness: 0.4,
    }),
    wallTrim: new THREE.MeshStandardMaterial({ color: 0x6366f1, emissive: 0x4f46e5, emissiveIntensity: 0.3 }),
    deskSurface: new THREE.MeshStandardMaterial({ color: 0x1e2230, roughness: 0.4, metalness: 0.2 }),
    deskLegs: new THREE.MeshStandardMaterial({ color: 0x0a0d14, roughness: 0.7 }),
    woodBoardroom: new THREE.MeshStandardMaterial({ color: 0x1e1b4b, roughness: 0.3, metalness: 0.3 }),
    leatherChair: new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.5 }),
    screenGlow: new THREE.MeshBasicMaterial({ color: 0x38bdf8 }),
    neonGreen: new THREE.MeshBasicMaterial({ color: 0x10b981 }),
    plantGreen: new THREE.MeshStandardMaterial({ color: 0x15803d, roughness: 0.6 }),
  };

  // 1. Main Floor (36m x 30m)
  const floorGeo = new THREE.BoxGeometry(36, 0.4, 30);
  const floor = new THREE.Mesh(floorGeo, materials.floor);
  floor.position.y = -0.2;
  floor.receiveShadow = true;
  _officeScene.add(floor);

  // Subtle Floor Grid Helper
  const gridHelper = new THREE.GridHelper(36, 36, 0x312e81, 0x1e293b);
  gridHelper.position.y = 0.02;
  _officeScene.add(gridHelper);

  // 2. Glass Perimeter Walls with Glowing Trims
  createWall(0, 2, -15, 36, 4, 0.3, materials.wallGlass, materials.wallTrim); // Back
  createWall(-18, 2, 0, 0.3, 4, 30, materials.wallGlass, materials.wallTrim); // Left
  createWall(18, 2, 0, 0.3, 4, 30, materials.wallGlass, materials.wallTrim);  // Right

  // 3. Central Boardroom Table & Chairs
  const tableGroup = new THREE.Group();
  const tableTopGeo = new THREE.CylinderGeometry(3.6, 3.6, 0.15, 32);
  tableTopGeo.scale(1.4, 1, 0.85); // Oval
  const tableTop = new THREE.Mesh(tableTopGeo, materials.woodBoardroom);
  tableTop.position.y = 1.0;
  tableTop.castShadow = true;
  tableTop.receiveShadow = true;
  tableGroup.add(tableTop);

  // Center Hologram Projector on Boardroom Table
  const holoGeo = new THREE.CylinderGeometry(0.5, 0.6, 0.1, 16);
  const holoBase = new THREE.Mesh(holoGeo, materials.wallTrim);
  holoBase.position.y = 1.1;
  tableGroup.add(holoBase);

  const holoRaysGeo = new THREE.ConeGeometry(1.2, 1.8, 16, 1, true);
  const holoRaysMat = new THREE.MeshBasicMaterial({ color: 0x6366f1, transparent: true, opacity: 0.25, wireframe: true });
  const holoRays = new THREE.Mesh(holoRaysGeo, holoRaysMat);
  holoRays.position.y = 2.0;
  holoRays.rotation.x = Math.PI;
  tableGroup.add(holoRays);

  // Table Legs
  const legGeo = new THREE.CylinderGeometry(0.12, 0.12, 1.0, 12);
  [[-2, 0.5, -1], [2, 0.5, -1], [-2, 0.5, 1], [2, 0.5, 1]].forEach(lp => {
    const leg = new THREE.Mesh(legGeo, materials.deskLegs);
    leg.position.set(...lp);
    tableGroup.add(leg);
  });

  // 6 Boardroom Executive Chairs
  const chairPositions = [
    [-2.2, 0, -1.8, 0], [0, 0, -2.1, 0], [2.2, 0, -1.8, 0],
    [-2.2, 0, 1.8, Math.PI], [0, 0, 2.1, Math.PI], [2.2, 0, 1.8, Math.PI]
  ];
  chairPositions.forEach(cp => {
    const chair = createOfficeChair(materials.leatherChair);
    chair.position.set(cp[0], 0, cp[1]);
    chair.rotation.y = cp[2];
    tableGroup.add(chair);
  });
  _officeScene.add(tableGroup);

  // 4. Coffee Lounge & Break Area (x: 0, z: -10)
  buildCoffeeLounge(materials);

  // 5. Presentation / Deliverable Stage (x: 0, z: 10)
  buildPresentationStage(materials);

  // 6. Build 6 Dedicated Workstations for Employees
  Object.values(OFFICE_EMPLOYEE_DEFS).forEach(def => {
    buildEmployeeDesk(def, materials);
  });

  // 7. Decorative Potted Plants & Partitions
  [[-14, 0, -12], [14, 0, -12], [-14, 0, 12], [14, 0, 12], [-4, 0, -14], [4, 0, -14]].forEach(pp => {
    createPottedPlant(pp[0], pp[2], materials);
  });
}

function createWall(x, y, z, w, h, d, glassMat, trimMat) {
  const wallGroup = new THREE.Group();
  const glass = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), glassMat);
  wallGroup.add(glass);

  // Glowing Top Trim
  const topTrim = new THREE.Mesh(new THREE.BoxGeometry(w, 0.12, d + 0.05), trimMat);
  topTrim.position.y = h / 2;
  wallGroup.add(topTrim);

  wallGroup.position.set(x, y, z);
  _officeScene.add(wallGroup);
}

function createOfficeChair(material) {
  const chairGroup = new THREE.Group();

  // Seat
  const seat = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.1, 0.7), material);
  seat.position.y = 0.55;
  chairGroup.add(seat);

  // Backrest
  const back = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.8, 0.1), material);
  back.position.set(0, 0.95, -0.32);
  chairGroup.add(back);

  // Base stem & wheels
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.5, 8), material);
  stem.position.y = 0.25;
  chairGroup.add(stem);

  const starGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.04, 5);
  const star = new THREE.Mesh(starGeo, material);
  star.position.y = 0.04;
  chairGroup.add(star);

  return chairGroup;
}

function buildCoffeeLounge(materials) {
  const lounge = new THREE.Group();
  lounge.position.set(0, 0, -10.5);

  // Coffee counter bar
  const bar = new THREE.Mesh(new THREE.BoxGeometry(3.5, 1.1, 1.0), materials.deskSurface);
  bar.position.y = 0.55;
  bar.castShadow = true;
  lounge.add(bar);

  // Espresso Machine
  const machine = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.6, 0.6), materials.wallTrim);
  machine.position.set(-0.8, 1.4, 0);
  lounge.add(machine);

  // Water Cooler (cylinder + blue bottle)
  const coolerBase = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.9, 16), materials.deskSurface);
  coolerBase.position.set(1.0, 0.45, 0);
  lounge.add(coolerBase);

  const coolerBottle = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.6, 16), materials.wallGlass);
  coolerBottle.position.set(1.0, 1.15, 0);
  lounge.add(coolerBottle);

  // Small Coffee Table & Cozy Lounge Chairs
  const cTable = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.0, 0.45, 24), materials.woodBoardroom);
  cTable.position.set(0, 0.22, 2.5);
  lounge.add(cTable);

  const sofaMat = new THREE.MeshStandardMaterial({ color: 0x312e81, roughness: 0.6 });
  const sofa = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.6, 0.9), sofaMat);
  sofa.position.set(0, 0.3, 3.8);
  sofa.rotation.y = Math.PI;
  lounge.add(sofa);

  _officeScene.add(lounge);
}

function buildPresentationStage(materials) {
  const stage = new THREE.Group();
  stage.position.set(0, 0, 10.5);

  // Raised platform
  const plat = new THREE.Mesh(new THREE.BoxGeometry(6.0, 0.2, 3.2), materials.deskSurface);
  plat.position.y = 0.1;
  stage.add(plat);

  // Smart Digital Whiteboard (Owner HITL Dashboard)
  const boardFrame = new THREE.Mesh(new THREE.BoxGeometry(4.2, 2.2, 0.1), materials.deskLegs);
  boardFrame.position.set(0, 1.8, 0.8);
  stage.add(boardFrame);

  const boardScreen = new THREE.Mesh(new THREE.BoxGeometry(4.0, 2.0, 0.05), new THREE.MeshBasicMaterial({ color: 0x1e1b4b }));
  boardScreen.position.set(0, 1.8, 0.85);
  stage.add(boardScreen);

  // Podium
  const podium = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.2, 0.6), materials.wallTrim);
  podium.position.set(0, 0.7, -0.4);
  stage.add(podium);

  _officeScene.add(stage);
}

function buildEmployeeDesk(def, materials) {
  const deskGroup = new THREE.Group();
  deskGroup.position.set(...def.deskPos);
  deskGroup.rotation.y = def.deskRot;

  // 1. Desk Surface
  const top = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.1, 1.3), materials.deskSurface);
  top.position.y = 0.95;
  top.castShadow = true;
  top.receiveShadow = true;
  deskGroup.add(top);

  // Legs
  const legGeo = new THREE.CylinderGeometry(0.06, 0.06, 0.95, 12);
  [[-1.1, 0.475, -0.55], [1.1, 0.475, -0.55], [-1.1, 0.475, 0.55], [1.1, 0.475, 0.55]].forEach(lp => {
    const leg = new THREE.Mesh(legGeo, materials.deskLegs);
    leg.position.set(...lp);
    deskGroup.add(leg);
  });

  // 2. Monitors setup based on employee specialty
  const isDev = def.id === '03_developer';
  const isMarketing = def.id === '02_การตลาด_ai';
  const isDevOps = def.id === '06_devops';

  if (isDev) {
    // Triple curved monitor for Developer Bint
    createMonitor(deskGroup, 0, 1.35, -0.2, 0.9, 0.5, def.color);
    createMonitor(deskGroup, -0.85, 1.35, -0.1, 0.8, 0.5, def.color, 0.28);
    createMonitor(deskGroup, 0.85, 1.35, -0.1, 0.8, 0.5, def.color, -0.28);

    // Mini CPU Server Tower under desk
    const tower = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.65, 0.6), materials.wallTrim);
    tower.position.set(0.8, 0.33, 0);
    deskGroup.add(tower);
  } else if (isMarketing) {
    // Dual monitor + Ring light on tripod for Lisa
    createMonitor(deskGroup, -0.4, 1.35, -0.2, 0.9, 0.55, def.color);
    createMonitor(deskGroup, 0.55, 1.35, -0.2, 0.9, 0.55, def.color, -0.15);

    // Studio Ring Light
    const ringGeo = new THREE.TorusGeometry(0.28, 0.04, 16, 32);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.position.set(0.9, 1.7, 0.2);
    deskGroup.add(ring);
  } else if (isDevOps) {
    // DevOps Kong: Wide Console Monitor + Server Racks behind
    createMonitor(deskGroup, 0, 1.4, -0.2, 1.3, 0.65, def.color);

    // 2 Server Racks behind the desk
    const rackGeo = new THREE.BoxGeometry(1.0, 2.6, 0.8);
    const rackMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.6 });
    [-1.2, 1.2].forEach(rx => {
      const rack = new THREE.Mesh(rackGeo, rackMat);
      rack.position.set(rx, 1.3, -1.8);
      deskGroup.add(rack);

      // Blinking LEDs
      const ledGeo = new THREE.BoxGeometry(0.7, 0.05, 0.05);
      const led = new THREE.Mesh(ledGeo, new THREE.MeshBasicMaterial({ color: 0x10b981 }));
      led.position.set(rx, 1.8, -1.38);
      deskGroup.add(led);
    });
  } else {
    // Standard sleek dual monitors
    createMonitor(deskGroup, -0.45, 1.35, -0.2, 0.85, 0.55, def.color);
    createMonitor(deskGroup, 0.45, 1.35, -0.2, 0.85, 0.55, def.color);
  }

  // Keyboard & Mouse
  const kb = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.02, 0.25), materials.deskLegs);
  kb.position.set(0, 1.01, 0.2);
  deskGroup.add(kb);

  // Executive Chair
  const chair = createOfficeChair(materials.leatherChair);
  chair.position.set(0, 0, 0.9);
  deskGroup.add(chair);

  // Interaction Hitbox on Desk
  const hitBox = new THREE.Mesh(
    new THREE.BoxGeometry(2.6, 2.0, 2.4),
    new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, wireframe: false })
  );
  hitBox.position.set(0, 1.0, 0);
  hitBox.userData = { isDesk: true, agentId: def.id };
  deskGroup.add(hitBox);
  _officeClickableObjects.push(hitBox);

  _officeScene.add(deskGroup);
}

function createMonitor(parent, x, y, z, w, h, screenColorHex, rotY = 0) {
  const group = new THREE.Group();
  group.position.set(x, y, z);
  group.rotation.y = rotY;

  // Bezel
  const bezel = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.04), new THREE.MeshStandardMaterial({ color: 0x050505 }));
  bezel.castShadow = true;
  group.add(bezel);

  // Screen
  const screen = new THREE.Mesh(
    new THREE.PlaneGeometry(w - 0.06, h - 0.06),
    new THREE.MeshBasicMaterial({ color: screenColorHex })
  );
  screen.position.z = 0.025;
  group.add(screen);

  // Stand
  const stand = new THREE.Mesh(
    new THREE.BoxGeometry(0.08, y - 0.95, 0.08),
    new THREE.MeshStandardMaterial({ color: 0x111111 })
  );
  stand.position.set(0, -(y - 0.95) / 2, 0);
  group.add(stand);

  parent.add(group);
}

function createPottedPlant(x, z, materials) {
  const plantGroup = new THREE.Group();
  plantGroup.position.set(x, 0, z);

  // Modern Pot
  const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.3, 0.7, 16), materials.deskSurface);
  pot.position.y = 0.35;
  plantGroup.add(pot);

  // Leaves
  const leaves = new THREE.Mesh(new THREE.DodecahedronGeometry(0.55), materials.plantGreen);
  leaves.position.y = 0.9;
  plantGroup.add(leaves);

  _officeScene.add(plantGroup);
}

// ═══════════════════════════════════════════════════════════════
//  4. 3D AI EMPLOYEE AVATARS & MOVEMENT ENGINE
// ═══════════════════════════════════════════════════════════════

function buildOfficeEmployees() {
  Object.values(OFFICE_EMPLOYEE_DEFS).forEach(def => {
    const agent = createEmployeeModel(def);
    _officeEmployees[def.id] = agent;
    _officeScene.add(agent.root);
    _officeClickableObjects.push(agent.hitBox);
  });
}

function createEmployeeModel(def) {
  const root = new THREE.Group();
  const [dx, dy, dz] = def.chairPos;
  root.position.set(dx, 0, dz);

  // Materials
  const skinMat = new THREE.MeshStandardMaterial({ color: 0xfbbf24, roughness: 0.6 });
  const shirtMat = new THREE.MeshStandardMaterial({ color: def.shirtColor, roughness: 0.5 });
  const pantsMat = new THREE.MeshStandardMaterial({ color: def.pantsColor, roughness: 0.6 });
  const hairMat = new THREE.MeshStandardMaterial({ color: 0x171717, roughness: 0.4 });
  const shoeMat = new THREE.MeshStandardMaterial({ color: 0x050505 });

  // 1. Torso
  const torso = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.7, 0.35), shirtMat);
  torso.position.y = 1.05;
  torso.castShadow = true;
  root.add(torso);

  // 2. Head
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.24, 16, 16), skinMat);
  head.position.y = 1.6;
  head.castShadow = true;
  root.add(head);

  // Hair / Cap
  const hair = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.18, 0.52), hairMat);
  hair.position.set(0, 1.74, 0);
  root.add(hair);

  // Smart Glasses for Bint & Mook
  if (def.id === '03_developer' || def.id === '04_data_analyst') {
    const glasses = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.08, 0.08), new THREE.MeshBasicMaterial({ color: 0x000000 }));
    glasses.position.set(0, 1.62, 0.22);
    root.add(glasses);
  }

  // 3. Limbs (Arms & Legs for walking cycle)
  const armGeo = new THREE.BoxGeometry(0.16, 0.6, 0.16);
  const leftArm = new THREE.Mesh(armGeo, shirtMat);
  leftArm.position.set(-0.36, 1.05, 0);
  root.add(leftArm);

  const rightArm = new THREE.Mesh(armGeo, shirtMat);
  rightArm.position.set(0.36, 1.05, 0);
  root.add(rightArm);

  const legGeo = new THREE.BoxGeometry(0.2, 0.7, 0.2);
  const leftLeg = new THREE.Mesh(legGeo, pantsMat);
  leftLeg.position.set(-0.16, 0.35, 0);
  leftLeg.castShadow = true;
  root.add(leftLeg);

  const rightLeg = new THREE.Mesh(legGeo, pantsMat);
  rightLeg.position.set(0.16, 0.35, 0);
  rightLeg.castShadow = true;
  root.add(rightLeg);

  // 4. Status Beacon Light above head
  const beaconGeo = new THREE.SphereGeometry(0.1, 12, 12);
  const beaconMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
  const beacon = new THREE.Mesh(beaconGeo, beaconMat);
  beacon.position.y = 2.05;
  root.add(beacon);

  // 5. Billboard Name Tag
  const nameSprite = createTextBillboard(`${def.name} (${def.role.split(' ')[0]})`, '#ffffff', '#1e1b4b');
  nameSprite.position.set(0, 2.35, 0);
  nameSprite.scale.set(2.8, 0.7, 1);
  root.add(nameSprite);

  // 6. Floating Live Thought Bubble Billboard
  const thoughtSprite = createTextBillboard(`💭 "${def.defaultThought}"`, '#38bdf8', 'rgba(10, 14, 23, 0.85)');
  thoughtSprite.position.set(0, 3.0, 0);
  thoughtSprite.scale.set(4.0, 0.85, 1);
  thoughtSprite.visible = true;
  root.add(thoughtSprite);

  // 7. Clickable Hitbox
  const hitBox = new THREE.Mesh(
    new THREE.CylinderGeometry(0.65, 0.65, 2.6, 8),
    new THREE.MeshBasicMaterial({ transparent: true, opacity: 0 })
  );
  hitBox.position.y = 1.3;
  hitBox.userData = { isAgent: true, agentId: def.id };
  root.add(hitBox);

  return {
    def: def,
    root: root,
    torso: torso,
    head: head,
    leftArm: leftArm,
    rightArm: rightArm,
    leftLeg: leftLeg,
    rightLeg: rightLeg,
    beacon: beacon,
    nameSprite: nameSprite,
    thoughtSprite: thoughtSprite,
    hitBox: hitBox,
    // Movement State
    homePos: new THREE.Vector3(...def.chairPos),
    currentPos: new THREE.Vector3(...def.chairPos),
    targetPos: new THREE.Vector3(...def.chairPos),
    isWalking: false,
    isSitting: true,
    walkSpeed: 3.2,
    walkCycle: 0,
    wanderCooldown: Math.random() * 8 + 6,
    // Simulation Live State
    status: 'idle',
    actionText: 'พร้อมปฏิบัติงาน',
    thoughtText: def.defaultThought,
    progress: 0,
  };
}

function createTextBillboard(text, textColor = '#ffffff', bgColor = 'rgba(15, 23, 42, 0.8)') {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');

  // Draw pill background
  ctx.fillStyle = bgColor;
  roundRect(ctx, 10, 10, 492, 108, 24, true, true);

  // Border
  ctx.lineWidth = 4;
  ctx.strokeStyle = '#6366f1';
  roundRect(ctx, 10, 10, 492, 108, 24, false, true);

  // Text
  ctx.fillStyle = textColor;
  ctx.font = 'bold 32px "Noto Sans Thai", Inter, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, 256, 64);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  const mat = new THREE.SpriteMaterial({ map: texture, depthTest: false });
  const sprite = new THREE.Sprite(mat);
  sprite.userData = { canvas, ctx, texture };
  return sprite;
}

function updateTextBillboard(sprite, text, textColor = '#ffffff', bgColor = 'rgba(15, 23, 42, 0.85)') {
  if (!sprite || !sprite.userData || !sprite.userData.canvas) return;
  const { canvas, ctx, texture } = sprite.userData;

  ctx.clearRect(0, 0, 512, 128);
  ctx.fillStyle = bgColor;
  roundRect(ctx, 10, 10, 492, 108, 24, true, true);

  ctx.lineWidth = 4;
  ctx.strokeStyle = '#6366f1';
  roundRect(ctx, 10, 10, 492, 108, 24, false, true);

  ctx.fillStyle = textColor;
  ctx.font = 'bold 28px "Noto Sans Thai", Inter, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  // Truncate if too long
  let display = text;
  if (display.length > 36) display = display.substring(0, 34) + '...';
  ctx.fillText(display, 256, 64);

  texture.needsUpdate = true;
}

function roundRect(ctx, x, y, width, height, radius, fill, stroke) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
  if (fill) ctx.fill();
  if (stroke) ctx.stroke();
}

// ═══════════════════════════════════════════════════════════════
//  5. ANIMATION LOOP & WALKING ENGINE ("เดินไปเดินมา")
// ═══════════════════════════════════════════════════════════════

let _clock = null;

function animateOffice() {
  _officeAnimId = requestAnimationFrame(animateOffice);

  if (!_clock && typeof THREE !== 'undefined' && THREE.Clock) {
    _clock = new THREE.Clock();
  }
  const delta = _clock ? Math.min(_clock.getDelta(), 0.1) : 0.016;
  const time = _clock ? _clock.getElapsedTime() : performance.now() * 0.001;

  // 1. Update Camera Smooth Orbit / Transitions
  if (_officeControls) _officeControls.update();

  if (_officeCameraTarget.active) {
    _officeCamera.position.lerp(_officeCameraTarget.pos, 0.05);
    _officeControls.target.lerp(_officeCameraTarget.lookAt, 0.05);
    if (_officeCamera.position.distanceTo(_officeCameraTarget.pos) < 0.2) {
      _officeCameraTarget.active = false;
    }
  }

  // 2. Update AI Employees Autonomous Behavior & Walking Animation
  Object.values(_officeEmployees).forEach(agent => {
    updateAgentMovement(agent, delta, time);
  });

  // 3. Render Scene
  if (_officeRenderer && _officeScene && _officeCamera) {
    _officeRenderer.render(_officeScene, _officeCamera);
  }
}

function updateAgentMovement(agent, delta, time) {
  // If Active Working or Awaiting Approval, override wandering
  if (['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(agent.status)) {
    // Return to desk immediately and work
    if (agent.targetPos.distanceTo(agent.homePos) > 0.5) {
      agent.targetPos.copy(agent.homePos);
      agent.isWalking = true;
    }
  } else if (agent.status === 'awaiting_confirmation') {
    // Walk to Presentation Stage to show deliverable to Owner!
    const stagePos = new THREE.Vector3(0, 0, 8.5);
    if (agent.targetPos.distanceTo(stagePos) > 0.5) {
      agent.targetPos.copy(stagePos);
      agent.isWalking = true;
    }
  } else {
    // IDLE: Autonomous Wandering Routine every 10-18 seconds
    agent.wanderCooldown -= delta;
    if (agent.wanderCooldown <= 0) {
      agent.wanderCooldown = Math.random() * 12 + 10;
      // 50% chance walk somewhere, 50% chance stay or return home
      if (Math.random() > 0.4) {
        const wp = OFFICE_WAYPOINTS[Math.floor(Math.random() * OFFICE_WAYPOINTS.length)];
        agent.targetPos.set(wp.pos[0] + (Math.random() * 0.8 - 0.4), 0, wp.pos[1] + (Math.random() * 0.8 - 0.4));
        agent.isWalking = true;
      } else {
        agent.targetPos.copy(agent.homePos);
        agent.isWalking = true;
      }
    }
  }

  // Walking Physics & Interpolation
  const dist = agent.currentPos.distanceTo(agent.targetPos);
  if (dist > 0.15) {
    agent.isWalking = true;
    agent.isSitting = false;

    // Movement direction
    const dir = new THREE.Vector3().subVectors(agent.targetPos, agent.currentPos).normalize();
    agent.currentPos.addScaledVector(dir, agent.walkSpeed * delta);
    agent.root.position.copy(agent.currentPos);

    // Smooth turn towards movement direction
    const targetAngle = Math.atan2(dir.x, dir.z);
    agent.root.rotation.y = THREE.MathUtils.lerp(agent.root.rotation.y, targetAngle, 0.12);

    // Walking Cycle (Legs & Arms swinging alternately + Torso bobbing)
    agent.walkCycle += delta * 10;
    const swing = Math.sin(agent.walkCycle);

    agent.leftLeg.rotation.x = swing * 0.55;
    agent.rightLeg.rotation.x = -swing * 0.55;
    agent.leftArm.rotation.x = -swing * 0.45;
    agent.rightArm.rotation.x = swing * 0.45;

    // Torso gentle bob
    agent.torso.position.y = 1.05 + Math.abs(Math.sin(agent.walkCycle * 2)) * 0.06;
  } else {
    // Stopped at destination
    agent.isWalking = false;
    agent.leftLeg.rotation.x = 0;
    agent.rightLeg.rotation.x = 0;

    // Check if at Home Desk
    if (agent.currentPos.distanceTo(agent.homePos) < 0.6) {
      agent.isSitting = true;
      agent.root.position.copy(agent.homePos);
      agent.root.rotation.y = agent.def.deskRot + Math.PI;

      // Typing motion if Active
      if (['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(agent.status)) {
        agent.leftArm.rotation.x = -0.7 + Math.sin(time * 12) * 0.1;
        agent.rightArm.rotation.x = -0.7 + Math.cos(time * 14) * 0.1;
      } else {
        // Resting arms on desk
        agent.leftArm.rotation.x = -0.4;
        agent.rightArm.rotation.x = -0.4;
      }
    } else {
      // Standing idle somewhere in office
      agent.leftArm.rotation.x = THREE.MathUtils.lerp(agent.leftArm.rotation.x, 0, 0.1);
      agent.rightArm.rotation.x = THREE.MathUtils.lerp(agent.rightArm.rotation.x, 0, 0.1);
    }
  }

  // Beacon Pulse
  if (agent.beacon) {
    if (agent.status === 'awaiting_confirmation') {
      agent.beacon.material.color.setHex(0xfbbf24);
      agent.beacon.scale.setScalar(1 + Math.sin(time * 8) * 0.4);
    } else if (['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(agent.status)) {
      agent.beacon.material.color.setHex(0x38bdf8);
      agent.beacon.scale.setScalar(1 + Math.sin(time * 6) * 0.3);
    } else {
      agent.beacon.material.color.setHex(0x10b981);
      agent.beacon.scale.setScalar(1);
    }
  }
}

// ═══════════════════════════════════════════════════════════════
//  6. LIVE STATE SYNC WITH BACKEND SIMULATION
// ═══════════════════════════════════════════════════════════════

async function syncOfficeWithSimState() {
  if (!_officeIsInitialized) return;

  try {
    const data = await apiGet('/api/simulation/state');
    if (!data || !data.agents) return;

    let activeCount = 0;

    data.agents.forEach(ag => {
      const empId = ag.department_id || ag.id;
      const agent = _officeEmployees[empId];
      if (!agent) return;

      agent.status = ag.status || 'idle';
      agent.actionText = ag.current_action || 'พร้อมปฏิบัติงาน';
      agent.thoughtText = ag.current_thought || agent.def.defaultThought;
      agent.progress = ag.progress || 0;

      if (['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(agent.status)) {
        activeCount++;
      }

      // Update Floating Thought Bubble
      let bubbleText = agent.thoughtText;
      if (agent.status === 'awaiting_confirmation') {
        bubbleText = '🚨 งานเสร็จแล้ว! รอ Owner อนุมัติ';
      } else if (['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(agent.status)) {
        bubbleText = `⚡ ${agent.actionText}`;
      }
      updateTextBillboard(agent.thoughtSprite, `💭 "${bubbleText}"`, '#38bdf8');
    });

    // Update Top Count Pill
    const countEl = document.getElementById('office3d-active-count');
    if (countEl) countEl.innerHTML = `⚡ กำลังทำงาน: <strong>${activeCount} คน</strong>`;

    // Update Inspector if currently open
    if (_officeSelectedAgentId) {
      updateInspectorDetails(_officeSelectedAgentId);
    }

  } catch (err) {
    console.warn('[Office3D] Sync warning:', err);
  }
}

// ═══════════════════════════════════════════════════════════════
//  7. INTERACTION, RAYCASTING & INSPECTOR CARD
// ═══════════════════════════════════════════════════════════════

function onOfficeMouseMove(e) {
  const container = document.getElementById('office3d-canvas-container');
  if (!container || !_officeCamera || !_officeRaycaster) return;

  const rect = container.getBoundingClientRect();
  _officeMouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  _officeMouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

  _officeRaycaster.setFromCamera(_officeMouse, _officeCamera);
  const intersects = _officeRaycaster.intersectObjects(_officeClickableObjects, false);

  if (intersects.length > 0) {
    const hit = intersects[0].object;
    const agentId = hit.userData.agentId;
    container.style.cursor = 'pointer';
    _officeHoveredAgent = agentId;
  } else {
    container.style.cursor = 'grab';
    _officeHoveredAgent = null;
  }
}

function onOfficeCanvasClick(e) {
  if (!_officeHoveredAgent) return;
  focusOnEmployee(_officeHoveredAgent);
}

function focusOnEmployee(empId) {
  const agent = _officeEmployees[empId];
  if (!agent) return;

  _officeSelectedAgentId = empId;

  // Camera smooth transition to employee desk
  const [dx, dy, dz] = agent.def.deskPos;
  _officeCameraTarget = {
    pos: new THREE.Vector3(dx + 5, 5, dz + 5),
    lookAt: new THREE.Vector3(dx, 1.2, dz),
    active: true,
  };

  // Open Inspector Card
  updateInspectorDetails(empId);
  const card = document.getElementById('office3d-inspector');
  if (card) card.style.display = 'block';
}

function updateInspectorDetails(empId) {
  const def = OFFICE_EMPLOYEE_DEFS[empId];
  const agent = _officeEmployees[empId];
  if (!def || !agent) return;

  const imgEl = document.getElementById('inspector-img');
  const nameEl = document.getElementById('inspector-name');
  const roleEl = document.getElementById('inspector-role');
  const deptEl = document.getElementById('inspector-dept');
  const dotEl = document.getElementById('inspector-status-dot');
  const textEl = document.getElementById('inspector-status-text');
  const thoughtEl = document.getElementById('inspector-thought');
  const pipEl = document.getElementById('inspector-pip');

  if (imgEl) imgEl.src = def.avatarUrl;
  if (nameEl) nameEl.textContent = def.name;
  if (roleEl) roleEl.textContent = def.role;
  if (deptEl) deptEl.textContent = `🏢 ${def.dept}`;

  let dot = '🟢';
  let text = 'พร้อมปฏิบัติงาน (Standby)';
  let pipClass = '';

  if (agent.status === 'awaiting_confirmation') {
    dot = '🚨';
    text = 'รอยืนยันอนุมัติปิดงาน (HITL)';
    pipClass = 'pending';
  } else if (['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(agent.status)) {
    dot = '⚡';
    text = `กำลังทำงาน: ${agent.actionText} (${agent.progress}%)`;
    pipClass = 'active';
  }

  if (dotEl) dotEl.textContent = dot;
  if (textEl) textEl.textContent = text;
  if (thoughtEl) thoughtEl.textContent = `"${agent.thoughtText}"`;
  if (pipEl) pipEl.className = `inspector-pip ${pipClass}`;
}

function closeOfficeInspector() {
  const card = document.getElementById('office3d-inspector');
  if (card) card.style.display = 'none';
  _officeSelectedAgentId = null;
}

function inspectAssignTask() {
  if (!_officeSelectedAgentId) return;
  if (typeof openDeptDispatchModal === 'function') {
    openDeptDispatchModal(_officeSelectedAgentId);
  }
}

function inspectViewWorkstation() {
  if (!_officeSelectedAgentId) return;
  if (typeof openEmployeeWorkstation === 'function') {
    openEmployeeWorkstation(_officeSelectedAgentId);
  }
}

function inspectChangeAvatar() {
  if (!_officeSelectedAgentId) return;
  if (typeof openAvatarModal === 'function') {
    openAvatarModal(_officeSelectedAgentId);
  }
}

// ═══════════════════════════════════════════════════════════════
//  8. HUD CONTROLS, PRESETS & QUICK DISPATCH
// ═══════════════════════════════════════════════════════════════

function setOfficeCameraPreset(presetKey, btnEl) {
  const p = OFFICE_CAMERA_PRESETS[presetKey];
  if (!p) return;

  _officeCameraTarget = {
    pos: new THREE.Vector3(...p.pos),
    lookAt: new THREE.Vector3(...p.target),
    active: true,
  };

  document.querySelectorAll('.camera-btn-group .hud-btn').forEach(b => {
    b.classList.remove('active');
  });
  if (btnEl) {
    btnEl.classList.add('active');
  } else if (typeof event !== 'undefined' && event && event.target) {
    event.target.classList.add('active');
  }
}

function toggleOfficeFreeRoam() {
  if (_officeControls) {
    _officeControls.autoRotate = !_officeControls.autoRotate;
    _officeControls.autoRotateSpeed = 1.0;
    const btn = document.getElementById('btn-office-freeroam');
    if (btn) btn.classList.toggle('active', _officeControls.autoRotate);
  }
}

function renderOfficeHudChips() {
  const container = document.getElementById('office3d-emp-chips');
  if (!container) return;

  container.innerHTML = Object.values(OFFICE_EMPLOYEE_DEFS).map(def => `
    <button class="emp-jump-chip" onclick="focusOnEmployee('${def.id}')">
      <img src="${def.avatarUrl}" class="chip-avatar-img" alt="${def.name}" onerror="this.src='/static/img/avatars/01_secretary.jpg'" />
      <span>${def.name}</span>
      <span class="chip-status-dot" id="chip-dot-${def.id}"></span>
    </button>
  `).join('');
}

async function dispatchFromOffice3D() {
  const input = document.getElementById('office3d-quick-input');
  if (!input || !input.value.trim()) {
    if (typeof toast === 'function') toast('กรุณาพิมพ์คำสั่งงานสำหรับทีม AI', 'warning');
    return;
  }

  const promptText = input.value.trim();
  input.value = '';

  try {
    if (typeof toast === 'function') toast(`🚀 ส่งคำสั่ง "${promptText.slice(0, 30)}..." เข้าสู่ทีม AI`, 'info');
    await apiPost('/api/simulation/start', {
      preset: 'custom',
      prompt: promptText
    });
    if (typeof toast === 'function') toast('เลขาอิงฟ้ามอบหมายงานให้ทีม AI แล้ว — ดูพวกเขาเดินไปทำงานได้เลย!', 'success');
    syncOfficeWithSimState();
  } catch (err) {
    if (typeof toast === 'function') toast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  }
}

async function quickRunOfficePreset(presetKey) {
  try {
    if (typeof toast === 'function') toast('🚀 สั่งเริ่มงานด่วน...', 'info');
    await apiPost('/api/simulation/start', {
      preset: presetKey,
      prompt: ''
    });
    if (typeof toast === 'function') toast('เริ่มงานเรียบร้อย — พนักงานเดินเข้าโต๊ะทำงานแล้ว!', 'success');
    syncOfficeWithSimState();
  } catch (err) {
    if (typeof toast === 'function') toast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  }
}

function onOfficeWindowResize() {
  const container = document.getElementById('office3d-canvas-container');
  if (!container || !_officeRenderer || !_officeCamera) return;

  const w = container.clientWidth;
  const h = container.clientHeight;
  if (w && h) {
    _officeCamera.aspect = w / h;
    _officeCamera.updateProjectionMatrix();
    _officeRenderer.setSize(w, h);
  }
}

// Global Window Exports
if (typeof window !== 'undefined') {
  window.initOffice3D = initOffice3D;
  window.setOfficeCameraPreset = setOfficeCameraPreset;
  window.toggleOfficeFreeRoam = toggleOfficeFreeRoam;
  window.focusOnEmployee = focusOnEmployee;
  window.closeOfficeInspector = closeOfficeInspector;
  window.inspectAssignTask = inspectAssignTask;
  window.inspectViewWorkstation = inspectViewWorkstation;
  window.inspectChangeAvatar = inspectChangeAvatar;
  window.dispatchFromOffice3D = dispatchFromOffice3D;
  window.quickRunOfficePreset = quickRunOfficePreset;
}
