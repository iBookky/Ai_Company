/* ═══════════════════════════════════════════════════════════════
   office3d.js — Real-World 3D Virtual AI Enterprise Office
   Warm Architectural Workspace, Live Department Monitors & Holographic Status
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
let _officeCameraTarget = { pos: null, lookAt: null, active: false, speed: 0.08 };

// Agents & World Objects
const _officeEmployees = {};
let _officeClickableObjects = [];
let _officeSyncInterval = null;
let _officeSpotlights = {};

// Camera Presets for Real-World Navigation
const OFFICE_CAMERA_PRESETS = {
  overview:    { pos: [22, 19, 22], target: [0, 1.2, 0], label: '🌐 ภาพรวม (Overview)' },
  isometric:   { pos: [22, 19, 22], target: [0, 1.2, 0], label: '🌐 ภาพรวม (Isometric)' },
  top:         { pos: [0, 30, 0.5], target: [0, 0, 0], label: '📐 ผังออฟฟิศ (Top-Down)' },
  boardroom:   { pos: [0, 5.5, 6.5], target: [0, 1.2, 0], label: '🏛️ ห้องประชุม' },
  lounge:      { pos: [0, 5.2, -6.0], target: [0, 1.2, -10.5], label: '☕ มุมกาแฟ & พักผ่อน' },
  // Department Closeups
  '01_secretary':    { pos: [-4.2, 3.8, -3.2], target: [-8, 1.4, -6], label: '🗂️ สำนักเลขาธิการ' },
  '03_developer':    { pos: [4.2, 3.8, -3.2], target: [8, 1.4, -6], label: '💻 ฝ่ายพัฒนาซอฟต์แวร์' },
  '02_การตลาด_ai':   { pos: [4.2, 3.8, 3.2], target: [8, 1.4, 6], label: '📣 ฝ่ายการตลาด & Content' },
  '04_data_analyst': { pos: [-4.2, 3.8, 3.2], target: [-8, 1.4, 6], label: '📊 ฝ่ายตรวจสอบคุณภาพ & Data' },
  '05_accounting':   { pos: [-8.0, 3.8, 0], target: [-12, 1.4, 0], label: '💰 ฝ่ายการเงิน & ต้นทุน Cloud' },
  '06_sales':        { pos: [8.0, 3.8, 0], target: [12, 1.4, 0], label: '🤝 ฝ่ายขายและบริการลูกค้า' },
};

// 6 AI Employees Master Specification
const OFFICE_EMPLOYEE_DEFS = {
  '01_secretary': {
    id: '01_secretary',
    name: 'อิงฟ้า',
    role: 'Executive Secretary & CKO',
    dept: 'สำนักเลขาธิการ & CKO',
    shortDept: 'เลขาธิการ & CKO',
    icon: '🗂️',
    color: 0x38bdf8,
    colorHex: '#38bdf8',
    deskPos: [-8, 0, -6],
    deskRot: Math.PI * 0.25,
    avatarUrl: '/static/img/avatars/01_secretary.jpg',
    defaultThought: 'วางแผนกลยุทธ์และจัดสรรงานให้ทุกแผนก',
    screenType: 'secretary',
  },
  '03_developer': {
    id: '03_developer',
    name: 'บิ๊นท์',
    role: 'Lead Full-Stack Developer',
    dept: 'ฝ่ายพัฒนาระบบซอฟต์แวร์',
    shortDept: 'ฝ่ายพัฒนาซอฟต์แวร์',
    icon: '💻',
    color: 0x818cf8,
    colorHex: '#818cf8',
    deskPos: [8, 0, -6],
    deskRot: -Math.PI * 0.25,
    avatarUrl: '/static/img/avatars/03_developer.jpg',
    defaultThought: 'ออกแบบสถาปัตยกรรม Backend & API',
    screenType: 'code',
  },
  '02_การตลาด_ai': {
    id: '02_การตลาด_ai',
    name: 'ลิซ่า',
    role: 'Head of Marketing & Social Content',
    dept: 'ฝ่ายการตลาด & Social Content',
    shortDept: 'ฝ่ายการตลาด & Content',
    icon: '📣',
    color: 0xf472b6,
    colorHex: '#f472b6',
    deskPos: [8, 0, 6],
    deskRot: -Math.PI * 0.75,
    avatarUrl: '/static/img/avatars/02_marketing.jpg',
    defaultThought: 'คิดสคริปต์ไวรัล TikTok & แคมเปญโปรโมต',
    screenType: 'marketing',
  },
  '04_data_analyst': {
    id: '04_data_analyst',
    name: 'มุก',
    role: 'Senior QA & Data Analyst',
    dept: 'ฝ่ายตรวจสอบคุณภาพ & Data',
    shortDept: 'ฝ่าย QA & Data',
    icon: '📊',
    color: 0x34d399,
    colorHex: '#34d399',
    deskPos: [-8, 0, 6],
    deskRot: Math.PI * 0.75,
    avatarUrl: '/static/img/avatars/04_data_analyst.jpg',
    defaultThought: 'ตรวจสอบ Code Review และ Funnel Conversion',
    screenType: 'data',
  },
  '05_accounting': {
    id: '05_accounting',
    name: 'พลอย',
    role: 'Finance & Cloud Cost Controller',
    dept: 'ฝ่ายการเงิน & ต้นทุน Cloud',
    shortDept: 'ฝ่ายการเงิน & บัญชี',
    icon: '💰',
    color: 0xa78bfa,
    colorHex: '#a78bfa',
    deskPos: [-12, 0, 0],
    deskRot: Math.PI * 0.5,
    avatarUrl: '/static/img/avatars/05_accounting.jpg',
    defaultThought: 'ควบคุมงบประมาณ API Token และจุดคุ้มทุน ROI',
    screenType: 'finance',
  },
  '06_sales': {
    id: '06_sales',
    name: 'พิมพ์',
    role: 'Head of Sales & Customer Service',
    dept: 'ฝ่ายขายและบริการลูกค้า (Sales & CS)',
    shortDept: 'ฝ่ายขาย & บริการลูกค้า',
    icon: '🤝',
    color: 0xfb923c,
    colorHex: '#fb923c',
    deskPos: [12, 0, 0],
    deskRot: -Math.PI * 0.5,
    avatarUrl: '/static/img/avatars/06_sales.jpg',
    defaultThought: 'ประสานงานดูแลลูกค้า เสนอ Solution และติดตามปิดการขาย 24/7',
    screenType: 'sales',
  },
};

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

  // 1. Scene with Warm Architectural Ambient Sky
  _officeScene = new THREE.Scene();
  _officeScene.background = new THREE.Color(0x141824); // Warm architectural dusk interior
  _officeScene.fog = new THREE.FogExp2(0x141824, 0.012);

  // 2. Camera (Perspective with real-world architectural view)
  const width = container.clientWidth || 1000;
  const height = container.clientHeight || 700;
  _officeCamera = new THREE.PerspectiveCamera(40, width / height, 0.1, 200);
  _officeCamera.position.set(22, 19, 22);

  // 3. Renderer with high-fidelity soft shadows
  _officeRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
  _officeRenderer.setSize(width, height);
  _officeRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  _officeRenderer.shadowMap.enabled = true;
  _officeRenderer.shadowMap.type = THREE.PCFSoftShadowMap;
  _officeRenderer.toneMapping = THREE.ACESFilmicToneMapping;
  _officeRenderer.toneMappingExposure = 1.15;
  container.innerHTML = '';
  container.appendChild(_officeRenderer.domElement);

  // 4. OrbitControls
  if (typeof THREE.OrbitControls !== 'undefined') {
    _officeControls = new THREE.OrbitControls(_officeCamera, _officeRenderer.domElement);
    _officeControls.enableDamping = true;
    _officeControls.dampingFactor = 0.05;
    _officeControls.maxPolarAngle = Math.PI / 2 - 0.06; // Prevent looking under floor
    _officeControls.minDistance = 4;
    _officeControls.maxDistance = 55;
    _officeControls.target.set(0, 1.2, 0);
  }

  // 5. Lighting Setup
  setupRealWorldLighting();

  // 6. Architecture & Desks
  buildRealWorldArchitecture();

  // 7. 6 AI Department Workstations & Employees
  buildOfficeEmployees();

  // 8. Render HUD Quick-Jump Dock
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
//  2. PROCEDURAL TEXTURES (WARM WOOD, SCREENS, BADGES)
// ═══════════════════════════════════════════════════════════════

// Procedural Warm Light Oak Parquet Hardwood Floor
function createWarmWoodTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 1024;
  const ctx = canvas.getContext('2d');

  // Base warm honey-oak tone
  ctx.fillStyle = '#9e7343';
  ctx.fillRect(0, 0, 1024, 1024);

  const plankH = 64;
  const plankW = 256;
  const tones = ['#b88a53', '#ae7f47', '#9c6f39', '#bf925b', '#a4753f', '#c99b64'];

  for (let y = 0; y < 1024; y += plankH) {
    const rowOffset = (Math.floor(y / plankH) % 2) * (plankW / 2);
    for (let x = -plankW; x < 1024 + plankW; x += plankW) {
      const rx = x + rowOffset;
      const color = tones[Math.abs(Math.floor((x * 11 + y * 17) % tones.length))];
      ctx.fillStyle = color;
      ctx.fillRect(rx + 2, y + 2, plankW - 4, plankH - 4);

      // Delicate wood grain lines
      ctx.strokeStyle = 'rgba(60, 35, 10, 0.12)';
      ctx.lineWidth = 1;
      for (let g = 8; g < plankH - 4; g += 10) {
        ctx.beginPath();
        ctx.moveTo(rx + 2, y + g);
        ctx.bezierCurveTo(
          rx + plankW * 0.3, y + g + Math.sin(rx + g) * 2,
          rx + plankW * 0.7, y + g - Math.cos(y + g) * 2,
          rx + plankW - 2, y + g
        );
        ctx.stroke();
      }

      // Plank Bevel & Joint Groove
      ctx.strokeStyle = 'rgba(35, 20, 8, 0.35)';
      ctx.lineWidth = 2;
      ctx.strokeRect(rx, y, plankW, plankH);

      // Light highlight on top edge of plank
      ctx.strokeStyle = 'rgba(255, 240, 210, 0.15)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(rx + 2, y + 2);
      ctx.lineTo(rx + plankW - 2, y + 2);
      ctx.stroke();
    }
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(6, 5);
  return texture;
}

// Procedural Real-World Screens (Code, Analytics, Marketing, Finance, DevOps)
function createMonitorScreenTexture(type, colorHex) {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 320;
  const ctx = canvas.getContext('2d');

  // Dark IDE/Dashboard Background
  ctx.fillStyle = '#0b0f19';
  ctx.fillRect(0, 0, 512, 320);

  // Window Top Title Bar
  ctx.fillStyle = '#1e293b';
  ctx.fillRect(0, 0, 512, 32);

  // Window Dots (Red, Yellow, Green)
  ctx.fillStyle = '#ef4444';
  ctx.beginPath(); ctx.arc(18, 16, 5, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#f59e0b';
  ctx.beginPath(); ctx.arc(36, 16, 5, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#10b981';
  ctx.beginPath(); ctx.arc(54, 16, 5, 0, Math.PI * 2); ctx.fill();

  // Title Text
  ctx.fillStyle = '#94a3b8';
  ctx.font = 'bold 12px "JetBrains Mono", monospace';
  ctx.fillText(`AI Enterprise Terminal — [${type.toUpperCase()}]`, 75, 20);

  if (type === 'code' || type === 'devops') {
    // Code Syntax / Server Logs
    ctx.font = '11px "JetBrains Mono", monospace';
    const lines = [
      { text: 'import fastapi, uvicorn, asyncio', color: '#f472b6' },
      { text: 'from enterprise.services import agent_service', color: '#38bdf8' },
      { text: 'app = FastAPI(title="AI Enterprise Engine")', color: '#818cf8' },
      { text: '', color: '' },
      { text: '@app.post("/api/agents/dispatch")', color: '#fbbf24' },
      { text: 'async def dispatch_task(payload: TaskModel):', color: '#60a5fa' },
      { text: '    worker = await queue.get_agent("03_developer")', color: '#34d399' },
      { text: '    return {"status": "ACTIVE", "progress": 82}', color: '#a78bfa' },
      { text: '    # Real-time WebSockets streaming updates...', color: '#64748b' },
      { text: '[200 OK] Uptime: 99.99% | Ping: 12ms', color: '#10b981' },
      { text: 'Docker container worker_dev: running healthy', color: '#38bdf8' },
    ];
    let ly = 60;
    lines.forEach((l, idx) => {
      ctx.fillStyle = '#475569';
      ctx.fillText(`${idx + 1}`.padStart(2, '0'), 14, ly);
      ctx.fillStyle = l.color || '#cbd5e1';
      ctx.fillText(l.text, 40, ly);
      ly += 22;
    });
  } else if (type === 'marketing') {
    // Video Timeline & Social Analytics
    ctx.fillStyle = '#ec4899';
    ctx.fillRect(20, 50, 220, 130);
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 14px sans-serif';
    ctx.fillText('🎬 Viral TikTok Video', 35, 100);
    ctx.font = '11px sans-serif';
    ctx.fillText('One-Person AI Enterprise 100%', 35, 125);

    // Timeline Track
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(20, 195, 472, 35);
    ctx.fillStyle = '#ec4899';
    ctx.fillRect(40, 202, 180, 20);
    ctx.fillStyle = '#8b5cf6';
    ctx.fillRect(230, 202, 140, 20);

    // Stats Card on Right
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(260, 50, 230, 130);
    ctx.fillStyle = '#34d399';
    ctx.font = 'bold 22px sans-serif';
    ctx.fillText('148,500', 280, 95);
    ctx.font = '11px sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Total Video Impressions (+38%)', 280, 120);
    ctx.fillStyle = '#38bdf8';
    ctx.fillText('Conversion: 12.4% | Leads: 642', 280, 145);
  } else if (type === 'finance') {
    // Financial Ledger & Token Cost Graphs
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(20, 50, 472, 110);
    ctx.fillStyle = '#a78bfa';
    ctx.font = 'bold 24px sans-serif';
    ctx.fillText('฿ 42,850.00', 35, 95);
    ctx.font = '11px sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Cloud Cost Efficiency | LLM Budget Cap: $100.00', 35, 125);

    // Bar chart
    const bars = [40, 65, 55, 90, 75, 120, 95, 140, 110];
    bars.forEach((bh, i) => {
      ctx.fillStyle = i === bars.length - 1 ? '#34d399' : '#818cf8';
      ctx.fillRect(35 + i * 50, 290 - bh, 36, bh);
    });
  } else if (type === 'sales') {
    // Sales CRM Pipeline & Customer Service Dashboard
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(20, 50, 225, 115);
    ctx.fillStyle = '#ea580c';
    ctx.fillRect(20, 50, 225, 28);
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 13px sans-serif';
    ctx.fillText('🤝 Enterprise CRM Pipeline', 32, 70);
    ctx.fillStyle = '#fed7aa';
    ctx.font = '11px sans-serif';
    ctx.fillText('B2B Solutions & Client Relations', 32, 98);
    ctx.fillStyle = '#fef08a';
    ctx.font = 'bold 15px sans-serif';
    ctx.fillText('Closed: ฿450,000 / Q4', 32, 122);
    ctx.fillStyle = '#38bdf8';
    ctx.font = '11px sans-serif';
    ctx.fillText('Active Qualified Leads: 28 Deals', 32, 145);

    // CSAT & Live Support Card on Right
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(260, 50, 232, 115);
    ctx.fillStyle = '#fb923c';
    ctx.font = 'bold 24px sans-serif';
    ctx.fillText('99.2% CSAT', 275, 95);
    ctx.font = '11px sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Omnichannel Support & Resolution', 275, 120);
    ctx.fillStyle = '#34d399';
    ctx.fillText('Avg Response: < 30s | SLA: 100%', 275, 145);

    // Pipeline Stage Bar
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(20, 195, 472, 35);
    ctx.fillStyle = '#fb923c';
    ctx.fillRect(35, 202, 150, 20);
    ctx.fillStyle = '#10b981';
    ctx.fillRect(195, 202, 140, 20);
    ctx.fillStyle = '#38bdf8';
    ctx.fillRect(345, 202, 130, 20);
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText('PROSPECT (10)', 45, 216);
    ctx.fillText('PROPOSAL (8)', 205, 216);
    ctx.fillText('CLOSED WON (10)', 355, 216);
  } else {
    // QA & Secretary / Executive KPI Dashboard
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(20, 50, 220, 100);
    ctx.fillStyle = '#10b981';
    ctx.font = 'bold 22px sans-serif';
    ctx.fillText('99.4% Pass', 35, 95);
    ctx.font = '11px sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Automated QA Test Suite Coverage', 35, 125);

    ctx.fillStyle = '#1e293b';
    ctx.fillRect(260, 50, 232, 100);
    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 22px sans-serif';
    ctx.fillText('6 Active AI', 275, 95);
    ctx.font = '11px sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Autonomous Company Operations', 275, 125);

    // Task check list
    ctx.font = '12px sans-serif';
    ctx.fillStyle = '#34d399';
    ctx.fillText('✔ 01 Secretary — Strategy & Daily Briefing', 35, 190);
    ctx.fillText('✔ 03 Developer — FastAPI Endpoints Clean', 35, 218);
    ctx.fillText('✔ 06 Sales & CS — Deal Pipeline Closed & CSAT 99%', 35, 246);
    ctx.fillText('✔ 05 Accounting — Budget under Threshold', 35, 274);
  }

  const texture = new THREE.CanvasTexture(canvas);
  return texture;
}

// ═══════════════════════════════════════════════════════════════
//  3. REAL-WORLD LIGHTING & ARCHITECTURE
// ═══════════════════════════════════════════════════════════════

function setupRealWorldLighting() {
  // 1. Natural Sky Fill (HemisphereLight: soft sky blue / warm floor bounce)
  const hemiLight = new THREE.HemisphereLight(0xdbeafe, 0x92673a, 0.75);
  _officeScene.add(hemiLight);

  // 2. Ambient Warm Light
  const ambient = new THREE.AmbientLight(0xffedd5, 0.45);
  _officeScene.add(ambient);

  // 3. Natural Sunlight Streaming from Windows (DirectionalLight)
  const sunLight = new THREE.DirectionalLight(0xfffaed, 1.25);
  sunLight.position.set(24, 28, 18);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.width = 2048;
  sunLight.shadow.mapSize.height = 2048;
  sunLight.shadow.camera.near = 5;
  sunLight.shadow.camera.far = 75;
  const d = 26;
  sunLight.shadow.camera.left = -d;
  sunLight.shadow.camera.right = d;
  sunLight.shadow.camera.top = d;
  sunLight.shadow.camera.bottom = -d;
  sunLight.shadow.bias = -0.0004;
  _officeScene.add(sunLight);

  // 4. Central Boardroom Chandelier Spotlight
  const centerLight = new THREE.SpotLight(0xfffaed, 1.1, 24, Math.PI / 4, 0.35);
  centerLight.position.set(0, 11, 0);
  centerLight.target.position.set(0, 0, 0);
  _officeScene.add(centerLight);
  _officeScene.add(centerLight.target);

  // 5. Warm Spotlights at each of the 6 Department Bays
  Object.values(OFFICE_EMPLOYEE_DEFS).forEach(def => {
    const spot = new THREE.SpotLight(0xffedd5, 0.7, 12, Math.PI / 3.5, 0.4);
    spot.position.set(def.deskPos[0], 6.5, def.deskPos[2]);
    spot.target.position.set(def.deskPos[0], 1, def.deskPos[2]);
    _officeScene.add(spot);
    _officeScene.add(spot.target);
    _officeSpotlights[def.id] = spot;
  });
}

function buildRealWorldArchitecture() {
  const woodTexture = createWarmWoodTexture();

  const materials = {
    floorWood: new THREE.MeshStandardMaterial({
      map: woodTexture,
      roughness: 0.35,
      metalness: 0.05,
    }),
    carpetWalkway: new THREE.MeshStandardMaterial({
      color: 0x222a38,
      roughness: 0.85,
    }),
    glassWall: new THREE.MeshPhysicalMaterial({
      color: 0xdbeafe,
      transparent: true,
      opacity: 0.32,
      roughness: 0.08,
      transmission: 0.88,
      thickness: 0.3,
    }),
    aluminumTrim: new THREE.MeshStandardMaterial({
      color: 0x475569,
      roughness: 0.25,
      metalness: 0.8,
    }),
    deskWoodOak: new THREE.MeshStandardMaterial({
      color: 0xdfbe93,
      roughness: 0.45,
    }),
    deskSteelMatte: new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      roughness: 0.6,
      metalness: 0.4,
    }),
    boardroomMarble: new THREE.MeshStandardMaterial({
      color: 0x1e2538,
      roughness: 0.18,
      metalness: 0.25,
    }),
    leatherExecutive: new THREE.MeshStandardMaterial({
      color: 0x1f2430,
      roughness: 0.55,
    }),
    plantGreen: new THREE.MeshStandardMaterial({
      color: 0x16a34a,
      roughness: 0.5,
    }),
    potWhiteCeramic: new THREE.MeshStandardMaterial({
      color: 0xf1f5f9,
      roughness: 0.15,
    }),
  };

  // 1. Main Parquet Hardwood Floor (38m x 32m)
  const floorGeo = new THREE.BoxGeometry(38, 0.4, 32);
  const floor = new THREE.Mesh(floorGeo, materials.floorWood);
  floor.position.y = -0.2;
  floor.receiveShadow = true;
  _officeScene.add(floor);

  // 2. Central Executive Walkway (Slate Grey Runner)
  const runnerGeo = new THREE.BoxGeometry(4.0, 0.02, 28);
  const runner = new THREE.Mesh(runnerGeo, materials.carpetWalkway);
  runner.position.set(0, 0.01, 0);
  runner.receiveShadow = true;
  _officeScene.add(runner);

  // Cross walkway connecting east/west wings
  const crossRunnerGeo = new THREE.BoxGeometry(32, 0.02, 3.6);
  const crossRunner = new THREE.Mesh(crossRunnerGeo, materials.carpetWalkway);
  crossRunner.position.set(0, 0.008, 0);
  crossRunner.receiveShadow = true;
  _officeScene.add(crossRunner);

  // 3. Perimeter Glass Curtain Windows with Modern Aluminum Mullions
  createPanoramicWindows(-19, 2.5, 0, 0.3, 5.0, 32, materials.glassWall, materials.aluminumTrim); // West
  createPanoramicWindows(19, 2.5, 0, 0.3, 5.0, 32, materials.glassWall, materials.aluminumTrim);  // East
  createPanoramicWindows(0, 2.5, -16, 38, 5.0, 0.3, materials.glassWall, materials.aluminumTrim); // North
  createPanoramicWindows(0, 2.5, 16, 38, 5.0, 0.3, materials.glassWall, materials.aluminumTrim);  // South

  // 4. Executive Boardroom Table & Modern Chairs (x: 0, z: 0)
  buildExecutiveBoardroom(materials);

  // 5. Break Lounge & Italian Espresso Bar (x: 0, z: -10.5)
  buildCoffeeLounge(materials);

  // 6. Presentation Wall with Smart LED Display (x: 0, z: 12)
  buildPresentationWall(materials);

  // 7. 6 Dedicated Department Bays
  Object.values(OFFICE_EMPLOYEE_DEFS).forEach(def => {
    buildDepartmentWorkstation(def, materials);
  });

  // 8. Realistic Indoor Plants (Monstera & Ficus in Ceramic Pots)
  [
    [-15, -13], [15, -13], [-15, 13], [15, 13],
    [-3.2, -6], [3.2, -6], [-3.2, 6], [3.2, 6],
    [-15, 0], [15, 0]
  ].forEach(([px, pz]) => {
    createOfficePlant(px, pz, materials);
  });
}

function createPanoramicWindows(x, y, z, w, h, d, glassMat, trimMat) {
  const group = new THREE.Group();

  // Glass Pane
  const glass = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), glassMat);
  group.add(glass);

  // Architectural Framing (Top/Bottom trims)
  const isZAxis = d > w;
  const frameGeo = isZAxis
    ? new THREE.BoxGeometry(w + 0.1, 0.16, d)
    : new THREE.BoxGeometry(w, 0.16, d + 0.1);

  const topTrim = new THREE.Mesh(frameGeo, trimMat);
  topTrim.position.y = h / 2;
  group.add(topTrim);

  const botTrim = new THREE.Mesh(frameGeo, trimMat);
  botTrim.position.y = -h / 2;
  group.add(botTrim);

  group.position.set(x, y, z);
  _officeScene.add(group);
}

function buildExecutiveBoardroom(materials) {
  const group = new THREE.Group();

  // Oval Executive Marble/Glass Conference Table
  const tableGeo = new THREE.CylinderGeometry(3.6, 3.6, 0.14, 32);
  tableGeo.scale(1.45, 1, 0.85); // Oval
  const tableTop = new THREE.Mesh(tableGeo, materials.boardroomMarble);
  tableTop.position.y = 1.05;
  tableTop.castShadow = true;
  tableTop.receiveShadow = true;
  group.add(tableTop);

  // Chrome Pedestal Base
  const baseGeo = new THREE.CylinderGeometry(0.8, 1.2, 1.0, 24);
  const base = new THREE.Mesh(baseGeo, materials.aluminumTrim);
  base.position.y = 0.52;
  group.add(base);

  // Conference Speakerphone Puck in Center
  const micGeo = new THREE.CylinderGeometry(0.4, 0.45, 0.08, 16);
  const mic = new THREE.Mesh(micGeo, materials.deskSteelMatte);
  mic.position.y = 1.15;
  group.add(mic);

  // Glowing center status ring
  const ringGeo = new THREE.RingGeometry(0.32, 0.36, 24);
  const ring = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: 0x38bdf8, side: THREE.DoubleSide }));
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = 1.195;
  group.add(ring);

  // 6 Executive High-Back Chairs around boardroom table
  const chairPos = [
    [-2.4, 0, -1.8, 0], [0, 0, -2.1, 0], [2.4, 0, -1.8, 0],
    [-2.4, 0, 1.8, Math.PI], [0, 0, 2.1, Math.PI], [2.4, 0, 1.8, Math.PI]
  ];
  chairPos.forEach(([cx, cy, cz, rotY]) => {
    const chair = createRealExecutiveChair(materials);
    chair.position.set(cx, 0, cz);
    chair.rotation.y = rotY;
    group.add(chair);
  });

  _officeScene.add(group);
}

function createRealExecutiveChair(materials) {
  const chair = new THREE.Group();

  // Seat with cushion curve
  const seat = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.12, 0.72), materials.leatherExecutive);
  seat.position.y = 0.58;
  seat.castShadow = true;
  chair.add(seat);

  // High Ergonomic Backrest
  const back = new THREE.Mesh(new THREE.BoxGeometry(0.68, 0.85, 0.1), materials.leatherExecutive);
  back.position.set(0, 1.02, -0.32);
  back.castShadow = true;
  chair.add(back);

  // Headrest
  const headrest = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.22, 0.08), materials.leatherExecutive);
  headrest.position.set(0, 1.5, -0.32);
  chair.add(headrest);

  // Chrome Armrests
  [-0.38, 0.38].forEach(ax => {
    const arm = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.28, 0.45), materials.aluminumTrim);
    arm.position.set(ax, 0.78, -0.05);
    chair.add(arm);
  });

  // Base Stem & 5-Star Wheels
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.5, 12), materials.aluminumTrim);
  stem.position.y = 0.26;
  chair.add(stem);

  const star = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 0.05, 5), materials.deskSteelMatte);
  star.position.y = 0.04;
  chair.add(star);

  return chair;
}

function buildCoffeeLounge(materials) {
  const lounge = new THREE.Group();
  lounge.position.set(0, 0, -10.8);

  // Modern Oak Coffee Bar Counter
  const bar = new THREE.Mesh(new THREE.BoxGeometry(4.2, 1.15, 1.1), materials.deskWoodOak);
  bar.position.y = 0.58;
  bar.castShadow = true;
  lounge.add(bar);

  // Commercial Italian Espresso Machine
  const machine = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.65, 0.65), materials.aluminumTrim);
  machine.position.set(-1.0, 1.48, 0);
  lounge.add(machine);

  // Coffee cups
  const cupGeo = new THREE.CylinderGeometry(0.08, 0.07, 0.12, 12);
  const cupMat = new THREE.MeshStandardMaterial({ color: 0xffffff });
  [-0.2, 0.1].forEach(cx => {
    const cup = new THREE.Mesh(cupGeo, cupMat);
    cup.position.set(cx, 1.21, 0.1);
    lounge.add(cup);
  });

  // Water Dispenser Cooler
  const cooler = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 1.0, 16), materials.potWhiteCeramic);
  cooler.position.set(1.4, 0.5, 0);
  lounge.add(cooler);
  const bottle = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.65, 16), materials.glassWall);
  bottle.position.set(1.4, 1.3, 0);
  lounge.add(bottle);

  // Cozy Velvet/Leather Lounge Sofa
  const sofaMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.7 });
  const sofa = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.65, 1.1), sofaMat);
  sofa.position.set(0, 0.33, 2.8);
  sofa.rotation.y = Math.PI;
  sofa.castShadow = true;
  lounge.add(sofa);

  // Low Oak Coffee Table with Magazines
  const cTable = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.35, 0.8), materials.deskWoodOak);
  cTable.position.set(0, 0.18, 1.6);
  cTable.castShadow = true;
  lounge.add(cTable);

  _officeScene.add(lounge);
}

function buildPresentationWall(materials) {
  const group = new THREE.Group();
  group.position.set(0, 0, 12.5);

  // 85" Ultra-HD Smart Presentation Board
  const screenW = 6.0;
  const screenH = 3.2;
  const frame = new THREE.Mesh(new THREE.BoxGeometry(screenW + 0.2, screenH + 0.2, 0.1), materials.deskSteelMatte);
  frame.position.y = 2.4;
  group.add(frame);

  const displayTexture = createMonitorScreenTexture('data', '#38bdf8');
  const screenMat = new THREE.MeshBasicMaterial({ map: displayTexture });
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(screenW, screenH), screenMat);
  screen.position.set(0, 2.4, 0.06);
  group.add(screen);

  _officeScene.add(group);
}

function createOfficePlant(x, z, materials) {
  const group = new THREE.Group();
  group.position.set(x, 0, z);

  // Modern Ceramic Plant Pot
  const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.35, 0.75, 16), materials.potWhiteCeramic);
  pot.position.y = 0.38;
  pot.castShadow = true;
  group.add(pot);

  // Lush Plant Leaves
  const leavesGeo = new THREE.DodecahedronGeometry(0.65, 1);
  const leaves = new THREE.Mesh(leavesGeo, materials.plantGreen);
  leaves.position.y = 1.05;
  leaves.scale.set(1, 1.3, 1);
  leaves.castShadow = true;
  group.add(leaves);

  _officeScene.add(group);
}

// ═══════════════════════════════════════════════════════════════
//  4. 6 DEPARTMENT WORKSTATIONS & 3D FLOATING STATUS BADGES
// ═══════════════════════════════════════════════════════════════

function buildDepartmentWorkstation(def, materials) {
  const group = new THREE.Group();
  const [dx, dy, dz] = def.deskPos;
  group.position.set(dx, 0, dz);
  group.rotation.y = def.deskRot;

  // 1. Floor Zone Label (Department name on floor)
  createFloorDepartmentLabel(group, def);

  // 2. Modern Ergonomic Oak Desk (2.4m x 1.1m)
  const topGeo = new THREE.BoxGeometry(2.4, 0.08, 1.1);
  const deskTop = new THREE.Mesh(topGeo, materials.deskWoodOak);
  deskTop.position.y = 0.96;
  deskTop.castShadow = true;
  deskTop.receiveShadow = true;
  group.add(deskTop);

  // Matte Black Steel Desk Legs
  const legGeo = new THREE.BoxGeometry(0.08, 0.96, 0.95);
  [-1.05, 1.05].forEach(lx => {
    const leg = new THREE.Mesh(legGeo, materials.deskSteelMatte);
    leg.position.set(lx, 0.48, 0);
    leg.castShadow = true;
    group.add(leg);
  });

  // 3. Desk Screens with Live Realistic Textures
  const screenTex = createMonitorScreenTexture(def.screenType, def.colorHex);

  if (def.id === '03_developer') {
    // Lead Dev: Triple Coding Monitors
    createMonitorMesh(group, -0.75, 1.45, -0.15, 0.85, 0.55, screenTex, 0.25);
    createMonitorMesh(group, 0, 1.45, -0.25, 1.0, 0.6, screenTex, 0);
    createMonitorMesh(group, 0.75, 1.45, -0.15, 0.85, 0.55, screenTex, -0.25);
  } else if (def.id === '06_sales') {
    // Sales & CS Lead Pim: Dual Curved Monitors + Client Conference Station
    createMonitorMesh(group, -0.5, 1.45, -0.2, 0.95, 0.55, screenTex, 0.15);
    createMonitorMesh(group, 0.5, 1.45, -0.2, 0.95, 0.55, screenTex, -0.15);

    // Executive Customer Trophy / Award Plaque behind Pim
    const plaqueBack = new THREE.Mesh(
      new THREE.BoxGeometry(1.8, 1.2, 0.08),
      new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.3, metalness: 0.2 })
    );
    plaqueBack.position.set(0, 2.0, -1.9);
    group.add(plaqueBack);

    const trophy = new THREE.Mesh(
      new THREE.CylinderGeometry(0.08, 0.12, 0.35, 16),
      new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.8, roughness: 0.2 })
    );
    trophy.position.set(1.05, 1.18, 0.1);
    group.add(trophy);
  } else if (def.id === '02_การตลาด_ai') {
    // Marketing: Dual Monitor + Studio Ring Light
    createMonitorMesh(group, -0.45, 1.45, -0.2, 0.9, 0.55, screenTex, 0.15);
    createMonitorMesh(group, 0.5, 1.45, -0.2, 0.9, 0.55, screenTex, -0.15);

    // Studio Ring Light
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(0.32, 0.035, 16, 32),
      new THREE.MeshBasicMaterial({ color: 0xffffff })
    );
    ring.position.set(1.0, 1.7, 0.1);
    group.add(ring);
  } else {
    // Standard Dual Curved Ultra-Wide Monitors
    createMonitorMesh(group, -0.48, 1.45, -0.2, 0.9, 0.55, screenTex, 0.12);
    createMonitorMesh(group, 0.48, 1.45, -0.2, 0.9, 0.55, screenTex, -0.12);
  }

  // Keyboard, Mouse, and Coffee Mug on Desk
  const kb = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.02, 0.22), materials.deskSteelMatte);
  kb.position.set(0, 1.01, 0.15);
  group.add(kb);

  const mug = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.05, 0.12, 12), new THREE.MeshStandardMaterial({ color: def.color }));
  mug.position.set(0.65, 1.06, 0.25);
  group.add(mug);

  // Executive Chair at Desk
  const chair = createRealExecutiveChair(materials);
  chair.position.set(0, 0, 0.85);
  group.add(chair);

  // Invisible Interaction Hitbox on Desk
  const hitBox = new THREE.Mesh(
    new THREE.BoxGeometry(2.8, 2.2, 2.6),
    new THREE.MeshBasicMaterial({ transparent: true, opacity: 0 })
  );
  hitBox.position.set(0, 1.2, 0);
  hitBox.userData = { isDesk: true, agentId: def.id };
  group.add(hitBox);
  _officeClickableObjects.push(hitBox);

  _officeScene.add(group);
}

function createFloorDepartmentLabel(parentGroup, def) {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');

  ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
  ctx.roundRect(8, 8, 496, 112, 16);
  ctx.fill();

  ctx.strokeStyle = def.colorHex;
  ctx.lineWidth = 4;
  ctx.roundRect(8, 8, 496, 112, 16);
  ctx.stroke();

  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 36px "Noto Sans Thai", sans-serif';
  ctx.fillText(`${def.icon} ${def.name}`, 30, 60);

  ctx.fillStyle = def.colorHex;
  ctx.font = '600 24px "Noto Sans Thai", sans-serif';
  ctx.fillText(def.shortDept, 30, 95);

  const texture = new THREE.CanvasTexture(canvas);
  const planeGeo = new THREE.PlaneGeometry(2.4, 0.6);
  const planeMat = new THREE.MeshBasicMaterial({ map: texture, transparent: true, opacity: 0.95 });
  const plane = new THREE.Mesh(planeGeo, planeMat);
  plane.rotation.x = -Math.PI / 2;
  plane.position.set(0, 0.02, 1.6);
  parentGroup.add(plane);
}

function createMonitorMesh(parent, x, y, z, w, h, screenTexture, rotY = 0) {
  const group = new THREE.Group();
  group.position.set(x, y, z);
  group.rotation.y = rotY;

  // Ultra-slim Bezel
  const bezel = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.04), new THREE.MeshStandardMaterial({ color: 0x090d16 }));
  bezel.castShadow = true;
  group.add(bezel);

  // Active Screen
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(w - 0.04, h - 0.04), new THREE.MeshBasicMaterial({ map: screenTexture }));
  screen.position.z = 0.022;
  group.add(screen);

  // Articulated Monitor Stand
  const stand = new THREE.Mesh(new THREE.BoxGeometry(0.08, y - 0.96, 0.08), new THREE.MeshStandardMaterial({ color: 0x1e293b }));
  stand.position.set(0, -(y - 0.96) / 2, 0);
  group.add(stand);

  parent.add(group);
}

// ═══════════════════════════════════════════════════════════════
//  5. REAL-WORLD AI EMPLOYEE AVATARS & 3D FLOATING STATUS HUD
// ═══════════════════════════════════════════════════════════════

function buildOfficeEmployees() {
  Object.values(OFFICE_EMPLOYEE_DEFS).forEach(def => {
    const agent = createRealWorldEmployee(def);
    _officeEmployees[def.id] = agent;
    _officeScene.add(agent.root);
    _officeClickableObjects.push(agent.hitBox);
  });
}

function createRealWorldEmployee(def) {
  const root = new THREE.Group();
  const [dx, dy, dz] = def.deskPos;
  // Position right at chair
  const chairOffset = new THREE.Vector3(0, 0, 0.85).applyAxisAngle(new THREE.Vector3(0, 1, 0), def.deskRot);
  root.position.set(dx + chairOffset.x, 0, dz + chairOffset.z);
  root.rotation.y = def.deskRot + Math.PI;

  // 1. Elegant Circular Halo Pedestal at Floor
  const haloGeo = new THREE.RingGeometry(0.45, 0.52, 32);
  const haloMat = new THREE.MeshBasicMaterial({ color: def.color, side: THREE.DoubleSide });
  const halo = new THREE.Mesh(haloGeo, haloMat);
  halo.rotation.x = -Math.PI / 2;
  halo.position.y = 0.03;
  root.add(halo);

  // 2. High-Res Circular Portrait Badge Avatar
  const loader = new THREE.TextureLoader();
  const avatarTex = loader.load(def.avatarUrl);

  const avatarGeo = new THREE.CircleGeometry(0.42, 32);
  const avatarMat = new THREE.MeshBasicMaterial({ map: avatarTex, side: THREE.DoubleSide });
  const avatarMesh = new THREE.Mesh(avatarGeo, avatarMat);
  avatarMesh.position.y = 1.35;
  avatarMesh.castShadow = true;
  root.add(avatarMesh);

  // Metallic & Glowing Bezel Rim around Avatar Portrait
  const rimGeo = new THREE.RingGeometry(0.42, 0.46, 32);
  const rimMat = new THREE.MeshBasicMaterial({ color: def.color, side: THREE.DoubleSide });
  const rim = new THREE.Mesh(rimGeo, rimMat);
  rim.position.y = 1.35;
  rim.position.z = 0.005;
  root.add(rim);

  // Acrylic Stand Stem
  const stem = new THREE.Mesh(
    new THREE.CylinderGeometry(0.04, 0.04, 0.8, 12),
    new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.6, roughness: 0.3 })
  );
  stem.position.y = 0.85;
  root.add(stem);

  // 3. Floating 3D Holographic Status Badge (Anchor at y: 2.8m above workstation)
  const statusSprite = create3DStatusSprite(def, '🟢 พร้อมปฏิบัติงาน', def.defaultThought);
  statusSprite.position.y = 2.8;
  root.add(statusSprite);

  // 4. Hitbox for clicking
  const hitBox = new THREE.Mesh(
    new THREE.BoxGeometry(1.6, 2.8, 1.6),
    new THREE.MeshBasicMaterial({ transparent: true, opacity: 0 })
  );
  hitBox.position.y = 1.4;
  hitBox.userData = { isAgent: true, agentId: def.id };
  root.add(hitBox);

  return {
    def,
    root,
    avatarMesh,
    halo,
    statusSprite,
    hitBox,
    status: 'idle',
    actionText: 'พร้อมปฏิบัติงาน',
    thoughtText: def.defaultThought,
    progress: 0,
    timeOffset: Math.random() * 10,
  };
}

// 3D World-Space Floating Billboard Sprite (Crisp Canvas Badge)
function create3DStatusSprite(def, statusText, thoughtText) {
  const canvas = document.createElement('canvas');
  canvas.width = 640;
  canvas.height = 240;
  const ctx = canvas.getContext('2d');

  updateStatusSpriteCanvas(ctx, canvas, def, statusText, thoughtText);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
  const sprite = new THREE.Sprite(spriteMat);
  sprite.scale.set(3.6, 1.35, 1);
  sprite.userData = { canvas, ctx, texture };
  return sprite;
}

function updateStatusSpriteCanvas(ctx, canvas, def, statusText, thoughtText) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Semi-transparent Glassmorphic Badge Container
  ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
  ctx.roundRect(10, 10, 620, 220, 24);
  ctx.fill();

  // Vibrant Department Border
  ctx.strokeStyle = def.colorHex;
  ctx.lineWidth = 4;
  ctx.roundRect(10, 10, 620, 220, 24);
  ctx.stroke();

  // Top Row: Icon + Name + Role
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 32px "Noto Sans Thai", sans-serif';
  ctx.fillText(`${def.icon} ${def.name} (${def.role})`, 30, 56);

  // Department Subtitle
  ctx.fillStyle = def.colorHex;
  ctx.font = '600 20px "Noto Sans Thai", sans-serif';
  ctx.fillText(def.dept, 30, 90);

  // Status Pill Box
  const isWorking = statusText.includes('กำลัง') || statusText.includes('Active') || statusText.includes('⚡');
  const isHitl = statusText.includes('อนุมัติ') || statusText.includes('HITL') || statusText.includes('🚨');

  const pillBg = isHitl ? 'rgba(245, 158, 11, 0.25)' : (isWorking ? 'rgba(16, 185, 129, 0.25)' : 'rgba(56, 189, 248, 0.2)');
  const pillBorder = isHitl ? '#f59e0b' : (isWorking ? '#10b981' : '#38bdf8');
  const dotColor = isHitl ? '#fbbf24' : (isWorking ? '#34d399' : '#38bdf8');

  ctx.fillStyle = pillBg;
  ctx.roundRect(30, 110, 580, 44, 12);
  ctx.fill();
  ctx.strokeStyle = pillBorder;
  ctx.lineWidth = 2;
  ctx.roundRect(30, 110, 580, 44, 12);
  ctx.stroke();

  // Glowing Dot
  ctx.fillStyle = dotColor;
  ctx.beginPath();
  ctx.arc(52, 132, 7, 0, Math.PI * 2);
  ctx.fill();

  // Status Text
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 20px "Noto Sans Thai", sans-serif';
  ctx.fillText(statusText, 72, 139);

  // Current Thought / Activity snippet
  ctx.fillStyle = '#cbd5e1';
  ctx.font = 'italic 18px "Noto Sans Thai", sans-serif';
  const cleanThought = (thoughtText || def.defaultThought || '').slice(0, 48);
  ctx.fillText(`"${cleanThought}${cleanThought.length >= 48 ? '...' : ''}"`, 30, 195);
}

// ═══════════════════════════════════════════════════════════════
//  6. ANIMATION LOOP & SMOOTH CAMERA GLIDE
// ═══════════════════════════════════════════════════════════════

function animateOffice() {
  _officeAnimId = requestAnimationFrame(animateOffice);

  const time = performance.now() * 0.001;

  // 1. Smooth Camera Gliding (Lerp Interpolation)
  if (_officeCameraTarget.active && _officeCamera && _officeControls) {
    const tPos = _officeCameraTarget.pos;
    const tLook = _officeCameraTarget.lookAt;
    const speed = _officeCameraTarget.speed || 0.08;

    _officeCamera.position.lerp(tPos, speed);
    _officeControls.target.lerp(tLook, speed);
    _officeControls.update();

    if (_officeCamera.position.distanceTo(tPos) < 0.15 &&
        _officeControls.target.distanceTo(tLook) < 0.15) {
      _officeCameraTarget.active = false;
    }
  } else if (_officeControls) {
    _officeControls.update();
  }

  // 2. Avatar Gentle Breathing & Activity Halos
  Object.values(_officeEmployees).forEach(agent => {
    // Gentle breathing elevation
    const breath = Math.sin(time * 2.5 + agent.timeOffset) * 0.04;
    agent.avatarMesh.position.y = 1.35 + breath;

    // Halo pulse if working
    if (['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(agent.status)) {
      const pulse = 1.0 + Math.sin(time * 6 + agent.timeOffset) * 0.15;
      agent.halo.scale.set(pulse, pulse, pulse);
    } else {
      agent.halo.scale.set(1, 1, 1);
    }
  });

  _officeRenderer.render(_officeScene, _officeCamera);
}

// ═══════════════════════════════════════════════════════════════
//  7. LIVE STATE SYNC WITH BACKEND SIMULATION
// ═══════════════════════════════════════════════════════════════

async function syncOfficeWithSimState() {
  if (!_officeIsInitialized) return;

  try {
    const data = await apiGet('/api/simulation/state');
    if (!data) return;

    let activeCount = 0;

    // Map agents from backend state
    if (data.agents && Array.isArray(data.agents)) {
      data.agents.forEach(a => {
        const agent = _officeEmployees[a.id];
        if (!agent) return;

        agent.status = a.status || 'idle';
        agent.actionText = a.action || 'พร้อมปฏิบัติงาน';
        agent.thoughtText = a.thought || a.current_thought || agent.def.defaultThought;
        agent.progress = a.progress || 0;

        let displayStatus = '🟢 พร้อมปฏิบัติงาน (Standby)';
        if (a.status === 'awaiting_confirmation') {
          displayStatus = '🚨 รอยืนยันอนุมัติปิดงาน (HITL)';
        } else if (['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(a.status)) {
          displayStatus = `⚡ กำลังทำงาน: ${a.action || 'ประมวลผล'} (${a.progress || 0}%)`;
          activeCount++;
        }

        // Update 3D Floating Sprite
        if (agent.statusSprite && agent.statusSprite.userData) {
          const { ctx, canvas, texture } = agent.statusSprite.userData;
          updateStatusSpriteCanvas(ctx, canvas, agent.def, displayStatus, agent.thoughtText);
          texture.needsUpdate = true;
        }

        // If inspector is open for this agent, update it
        if (_officeSelectedAgentId === a.id) {
          updateInspectorDetails(a.id);
        }
      });
    }

    const countEl = document.getElementById('office3d-active-count');
    if (countEl) {
      countEl.innerHTML = `⚡ กำลังทำงาน: <strong>${activeCount} คน</strong>`;
    }
  } catch (err) {
    console.warn('[Office3D] Sync warning:', err);
  }
}

// ═══════════════════════════════════════════════════════════════
//  8. INTERACTION, ONE-CLICK DEPARTMENT NAVIGATION & INSPECTOR
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
    container.style.cursor = 'pointer';
    _officeHoveredAgent = hit.userData.agentId;
  } else {
    container.style.cursor = 'grab';
    _officeHoveredAgent = null;
  }
}

function onOfficeCanvasClick() {
  if (!_officeHoveredAgent) return;
  focusOnDepartment(_officeHoveredAgent);
}

// Smooth One-Click Zoom into Any Department Bay
function focusOnDepartment(deptId) {
  const preset = OFFICE_CAMERA_PRESETS[deptId];
  const agent = _officeEmployees[deptId];
  if (!preset && !agent) return;

  _officeSelectedAgentId = deptId;

  // Cinematic 3/4 camera glide
  const [dx, dy, dz] = agent ? agent.def.deskPos : [0, 0, 0];
  const tPos = preset ? new THREE.Vector3(...preset.pos) : new THREE.Vector3(dx + 4.5, 4.0, dz + 4.5);
  const tLook = preset ? new THREE.Vector3(...preset.target) : new THREE.Vector3(dx, 1.4, dz);

  _officeCameraTarget = {
    pos: tPos,
    lookAt: tLook,
    active: true,
    speed: 0.08,
  };

  // Turn on highlight spotlight for this department
  Object.keys(_officeSpotlights).forEach(id => {
    if (_officeSpotlights[id]) {
      _officeSpotlights[id].intensity = (id === deptId) ? 1.4 : 0.45;
    }
  });

  // Highlight active chip in dock
  document.querySelectorAll('.emp-jump-chip').forEach(c => {
    c.classList.toggle('active', c.getAttribute('data-dept') === deptId);
  });

  // Open Inspector Card
  updateInspectorDetails(deptId);
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
  if (nameEl) nameEl.textContent = `${def.name} (${def.icon})`;
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

  // Restore regular department spotlights
  Object.values(_officeSpotlights).forEach(spot => {
    if (spot) spot.intensity = 0.7;
  });

  document.querySelectorAll('.emp-jump-chip').forEach(c => c.classList.remove('active'));
}

function setOfficeCameraPreset(presetKey, btnEl) {
  const p = OFFICE_CAMERA_PRESETS[presetKey];
  if (!p) return;

  _officeCameraTarget = {
    pos: new THREE.Vector3(...p.pos),
    lookAt: new THREE.Vector3(...p.target),
    active: true,
    speed: 0.07,
  };

  document.querySelectorAll('.camera-btn-group .hud-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) {
    btnEl.classList.add('active');
  }

  if (presetKey === 'overview' || presetKey === 'top' || presetKey === 'boardroom' || presetKey === 'lounge') {
    closeOfficeInspector();
  }
}

function toggleOfficeFreeRoam() {
  if (_officeControls) {
    _officeControls.autoRotate = !_officeControls.autoRotate;
    _officeControls.autoRotateSpeed = 0.8;
    const btn = document.getElementById('btn-office-freeroam');
    if (btn) btn.classList.toggle('active', _officeControls.autoRotate);
  }
}

// Render Department Navigation Dock with High-Res Avatars
function renderOfficeHudChips() {
  const container = document.getElementById('office3d-emp-chips');
  if (!container) return;

  container.innerHTML = Object.values(OFFICE_EMPLOYEE_DEFS).map(def => `
    <button class="emp-jump-chip" data-dept="${def.id}" onclick="focusOnDepartment('${def.id}')" title="ซูมไปยัง ${def.name}">
      <img src="${def.avatarUrl}" class="chip-avatar-img" alt="${def.name}" onerror="this.src='/static/img/avatars/01_secretary.jpg'" />
      <span class="chip-label">${def.icon} ${def.name}</span>
      <span class="chip-dept">${def.shortDept}</span>
    </button>
  `).join('');
}

async function dispatchFromOffice3D() {
  const input = document.getElementById('office3d-quick-input');
  if (!input || !input.value.trim()) return;

  const prompt = input.value.trim();
  input.value = '';

  if (typeof dispatchEnterpriseTask === 'function') {
    await dispatchEnterpriseTask(prompt);
  } else {
    try {
      await apiPost('/api/simulation/dispatch', { prompt });
    } catch (err) {
      console.error('[Office3D] Dispatch error:', err);
    }
  }

  setTimeout(syncOfficeWithSimState, 300);
}

function quickRunOfficePreset(presetKey) {
  const prompts = {
    systems_dev: 'พัฒนาระบบ Backend REST API พร้อม JWT Authentication และ Unit Tests',
    social_content: 'สร้าง Content Social Media: เปิดตัว One-Person AI Enterprise 100% (TikTok & Facebook)',
    sales: 'จัดทำแผนกลยุทธ์การขาย B2B Solution และระบบตอบกลับลูกค้า 24/7',
    devops: 'จัดทำแผนกลยุทธ์การขาย B2B Solution และระบบตอบกลับลูกค้า 24/7',
    data_analyst: 'ตรวจสอบ Code Review ความปลอดภัย และวิเคราะห์ Conversion Rate Funnel',
    accounting: 'ตรวจสอบรายงานรายรับ-รายจ่ายรายวัน และคำนวณ Token Cost ROI',
    secretary: 'จัดทำรายงานสรุปความคืบหน้าของทุกแผนก และอัปเดตลง company_memory.md',
  };

  const p = prompts[presetKey];
  if (p) {
    const input = document.getElementById('office3d-quick-input');
    if (input) input.value = p;
    dispatchFromOffice3D();
  }
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

function onOfficeWindowResize() {
  const container = document.getElementById('office3d-canvas-container');
  if (!container || !_officeCamera || !_officeRenderer) return;

  const width = container.clientWidth;
  const height = container.clientHeight;
  _officeCamera.aspect = width / height;
  _officeCamera.updateProjectionMatrix();
  _officeRenderer.setSize(width, height);
}

// Window Exports
if (typeof window !== 'undefined') {
  window.initOffice3D = initOffice3D;
  window.focusOnDepartment = focusOnDepartment;
  window.focusOnEmployee = focusOnDepartment; // Backward compatibility
  window.setOfficeCameraPreset = setOfficeCameraPreset;
  window.toggleOfficeFreeRoam = toggleOfficeFreeRoam;
  window.dispatchFromOffice3D = dispatchFromOffice3D;
  window.quickRunOfficePreset = quickRunOfficePreset;
  window.closeOfficeInspector = closeOfficeInspector;
  window.inspectAssignTask = inspectAssignTask;
  window.inspectViewWorkstation = inspectViewWorkstation;
  window.inspectChangeAvatar = inspectChangeAvatar;
}
