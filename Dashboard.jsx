import { useState, useEffect, useCallback, useRef } from "react";

/* ═══════════════════════════════════════════════════════════════════
   CONFIG — swap API_BASE to your Render URL when live
═══════════════════════════════════════════════════════════════════ */
const API_BASE = "https://jdas-digiclone-1.onrender.com";
const USE_MOCK = false;

/* ═══════════════════════════════════════════════════════════════════
   DESIGN TOKENS
═══════════════════════════════════════════════════════════════════ */
const T = {
  bg:"#f4ede4", bgSub:"#ede4d8", bgCard:"#faf7f3", bgDeep:"#e8ddd0",
  bgDark:"#1c2b1e", bgDarkMid:"#243228", bgDarkSub:"#2e3d32",
  border:"#d4c4ae", borderMid:"#b8a48e", borderDark:"#3d5240",
  green:"#2d6a4f", greenMid:"#40916c", greenLight:"#74c69d", greenPale:"#d8f3dc", greenGlow:"#52b788",
  gold:"#b5600a", goldMid:"#d4820f", goldLight:"#f4a261", goldPale:"#fdebd0",
  red:"#9b2226", redMid:"#ae2012", redLight:"#e63946", redPale:"#fde8e8",
  blue:"#1d3557", bluePale:"#dde8f0",
  textDark:"#1a1208", textMid:"#4a3728", textSoft:"#7a6352", textLight:"#a08878",
  white:"#fffcf8", shadow:"rgba(40,20,8,0.10)", shadowMd:"rgba(40,20,8,0.16)",
};

/* ═══════════════════════════════════════════════════════════════════
   MOCK DATA (used when USE_MOCK = true)
═══════════════════════════════════════════════════════════════════ */
const MOCK_DASHBOARD = {
  meta: { label:"live", week_of:"2026-03-09" },
  score: { xp:5, level:1, title:"Tough Week" },
  status_banner: {
    headline:"You're in a tough spot right now.",
    issues:[
      "More money is going out than coming in each week.",
      "You have 35h of work backed up — customers waiting 21 days.",
      "Customer satisfaction is low — delays are starting to hurt your reputation.",
    ],
    wins:[],
  },
  cash:      { amount:2100, weekly_out:820, weekly_in:320, weeks_left:2.6, net_12w:-9670, ending_cash:-4670, status:"NEGATIVE CASH", tax_reserve_12w:0 },
  workload:  { active_hrs:47, sustainable_cap:11.9, backlog_hrs:35, wait_days:21, stress_score:88, status:"OVERLOADED", hire_trigger:"HIRE TRIGGER" },
  pipeline:  { leads_per_week:2.4, qualified_per_week:0.84, proposals_12w:7.1, closes_12w:2.1, win_rate:0.30, avg_project_value:1425, revenue_12w:2993, cash_collected_12w:2844 },
  quality:   { score:61, label:"Poor", risk:"High", rework_rate:0.30, retention_likelihood:0.58, referral_likelihood:0.42, churn_risk:"High", reaction_score:62 },
  recurring: { mrr:0, mrr_month12:1802, stability_score:0, retainer_clients:0, coverage_pct:0, churn_flag:"TOO VOLATILE" },
  labor:     { team_capacity_wk:11.9, labor_cost_monthly:3897, gross_margin:0.53, sub_markup:0.33, num_subs:0 },
  badges:    { cash_pos:false, regular:false, helper:false, happy:false, breathing:false, pipeline:false, steady:false, legend:false },
};

/* ═══════════════════════════════════════════════════════════════════
   MOCK PROJECTS (pre-populated wizard)
═══════════════════════════════════════════════════════════════════ */
const MOCK_PROJECTS = [
  { id:1, code:"P-001", client:"Hartwell",  name:"Site Analysis",    hrs_remaining:2,  billing_rate:95, status:"Active" },
  { id:2, code:"P-002", client:"Morrow",    name:"Phase 2 Planning", hrs_remaining:23, billing_rate:95, status:"Active" },
  { id:3, code:"P-003", client:"Pinnacle",  name:"Full Audit",       hrs_remaining:38, billing_rate:95, status:"Active" },
  { id:4, code:"P-004", client:"Hartwell",  name:"Follow-up",        hrs_remaining:8,  billing_rate:95, status:"On Hold" },
];

/* ═══════════════════════════════════════════════════════════════════
   API HELPERS
═══════════════════════════════════════════════════════════════════ */
async function apiFetch(endpoint, options = {}) {
  if (USE_MOCK) {
    await new Promise(r => setTimeout(r, 600));
    if (endpoint === "/dashboard") return MOCK_DASHBOARD;
    if (endpoint === "/predict")   return { live: MOCK_DASHBOARD, predicted: MOCK_DASHBOARD, deltas: {} };
    return { status:"accepted" };
  }
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${endpoint} → ${res.status}`);
  return res.json();
}

/* ═══════════════════════════════════════════════════════════════════
   STATUS / XP HELPERS
═══════════════════════════════════════════════════════════════════ */
const statusColor  = s => s==="bad"||s==="NEGATIVE CASH"||s==="OVERLOADED"||s==="High"||s==="critical" ? T.red : s==="warn"||s==="LOW"||s==="TIGHT"||s==="Medium" ? T.gold : T.green;
const statusPale   = s => s==="bad"||s==="NEGATIVE CASH"||s==="OVERLOADED"||s==="High"||s==="critical" ? T.redPale : s==="warn"||s==="LOW"||s==="TIGHT"||s==="Medium" ? T.goldPale : T.greenPale;
const cashStatus   = d => d.cash.status==="NEGATIVE CASH"||d.cash.status==="CRITICAL" ? "bad" : d.cash.status==="LOW" ? "warn" : "good";
const workStatus   = d => d.workload.stress_score > 70 ? "bad" : d.workload.stress_score > 40 ? "warn" : "good";
const qualStatus   = d => d.quality.score < 60 ? "bad" : d.quality.score < 80 ? "warn" : "good";
const pipeStatus   = d => d.pipeline.win_rate < 0.35 ? "bad" : d.pipeline.win_rate < 0.45 ? "warn" : "good";

function xpLevel(xp) {
  if (xp>=90) return {level:5,title:"Business Legend",color:T.goldMid};
  if (xp>=70) return {level:4,title:"Running Smooth",color:T.greenMid};
  if (xp>=50) return {level:3,title:"Getting Traction",color:T.greenMid};
  if (xp>=30) return {level:2,title:"Finding Your Feet",color:T.goldMid};
  return          {level:1,title:"Tough Week",color:T.redMid};
}

const ACHIEVEMENTS = [
  { id:"cash_pos",  icon:"💰", name:"In the Green",     desc:"More coming in than going out" },
  { id:"regular",   icon:"🤝", name:"First Regular",    desc:"Signed your first regular client" },
  { id:"helper",    icon:"🧰", name:"Not Alone",        desc:"Hired your first helper" },
  { id:"happy",     icon:"😊", name:"Happy Customers",  desc:"Customer happiness hit 80+" },
  { id:"breathing", icon:"🌬️", name:"Room to Breathe", desc:"Work pile under control" },
  { id:"pipeline",  icon:"🔧", name:"Jobs Coming In",   desc:"Landing more than 1 job/week" },
  { id:"steady",    icon:"📅", name:"Steady Income",    desc:"Recurring covers half your costs" },
  { id:"legend",    icon:"🏆", name:"Business Legend",  desc:"Business score hit 90" },
];

/* ═══════════════════════════════════════════════════════════════════
   SHARED UI PRIMITIVES
═══════════════════════════════════════════════════════════════════ */
function HealthBar({ val, max=100, invert=false, size="md" }) {
  const pct = Math.min(100, Math.max(0, (val/max)*100));
  const eff = invert ? 100-pct : pct;
  const col = eff>66 ? T.green : eff>33 ? T.gold : T.red;
  const h   = size==="lg" ? 20 : size==="md" ? 13 : 8;
  return (
    <div style={{height:h,background:T.bgDeep,borderRadius:h,overflow:"hidden",border:`1.5px solid ${col}33`,boxShadow:`inset 0 2px 4px ${T.shadow}`}}>
      <div style={{height:"100%",width:`${eff}%`,background:`linear-gradient(90deg,${col}bb,${col})`,borderRadius:h,boxShadow:`0 0 10px ${col}55`,transition:"width 0.7s cubic-bezier(0.34,1.56,0.64,1)",position:"relative"}}>
        <div style={{position:"absolute",top:"15%",left:"6%",width:"30%",height:"40%",background:"rgba(255,255,255,0.28)",borderRadius:h}}/>
      </div>
    </div>
  );
}

function XPStrip({ xp }) {
  const {level,title,color} = xpLevel(xp);
  return (
    <div style={{display:"flex",flexDirection:"column",gap:6}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
        <div style={{display:"flex",gap:4}}>
          {Array.from({length:5},(_,i)=>(
            <span key={i} style={{fontSize:17,lineHeight:1,filter:i<level?"none":"grayscale(1) opacity(0.2)",transition:"filter 0.5s"}}>⭐</span>
          ))}
        </div>
        <span style={{fontSize:11,fontWeight:800,color}}>{title}</span>
      </div>
      <div style={{height:8,background:T.bgDeep,borderRadius:8,overflow:"hidden",border:`1.5px solid ${color}33`}}>
        <div style={{height:"100%",width:`${xp}%`,borderRadius:8,background:`linear-gradient(90deg,${color}99,${color})`,boxShadow:`0 0 8px ${color}66`,transition:"width 0.8s cubic-bezier(0.34,1.56,0.64,1)"}}/>
      </div>
      <div style={{fontSize:10,color:T.textLight,textAlign:"right"}}>Business Score: {xp} / 100</div>
    </div>
  );
}

function BadgeShelf({ badges }) {
  const [hov,setHov] = useState(null);
  return (
    <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
      {ACHIEVEMENTS.map(a=>{
        const earned = badges?.[a.id]||false;
        return (
          <div key={a.id} onMouseEnter={()=>setHov(a.id)} onMouseLeave={()=>setHov(null)}
            style={{position:"relative",width:48,height:48,borderRadius:12,
              background:earned?T.goldPale:T.bgDeep,
              border:`2px solid ${earned?T.goldMid:T.border}`,
              display:"flex",alignItems:"center",justifyContent:"center",fontSize:22,cursor:"default",
              filter:earned?"none":"grayscale(1) opacity(0.3)",
              boxShadow:earned?`0 3px 10px ${T.goldMid}44`:"none",
              transition:"all 0.3s",transform:hov===a.id?"scale(1.12) translateY(-2px)":"scale(1)"}}>
            {a.icon}
            {hov===a.id&&(
              <div style={{position:"absolute",bottom:"115%",left:"50%",transform:"translateX(-50%)",
                background:T.bgDark,color:T.white,borderRadius:10,padding:"8px 12px",
                fontSize:11,whiteSpace:"nowrap",zIndex:20,pointerEvents:"none",
                boxShadow:`0 6px 20px ${T.shadowMd}`,minWidth:160}}>
                <div style={{fontWeight:800,marginBottom:3}}>{a.name}</div>
                <div style={{opacity:0.7,fontSize:10}}>{a.desc}</div>
                <div style={{marginTop:4,fontSize:10,color:earned?T.greenLight:"#ff9a8b"}}>{earned?"✓ Earned":"🔒 Not yet"}</div>
                <div style={{position:"absolute",bottom:-6,left:"50%",transform:"translateX(-50%)",width:0,height:0,borderLeft:"6px solid transparent",borderRight:"6px solid transparent",borderTop:`6px solid ${T.bgDark}`}}/>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function StatusBanner({ banner }) {
  if (!banner) return null;
  const issues = banner.issues||[];
  const wins   = banner.wins||[];
  const s = issues.length>=2?"bad":issues.length===1?"warn":"good";
  const col=statusColor(s); const pale=statusPale(s);
  return (
    <div style={{background:pale,border:`2px solid ${col}44`,borderLeft:`5px solid ${col}`,borderRadius:14,padding:"14px 20px"}}>
      <div style={{fontSize:15,fontWeight:800,color:col==="bad"?T.redMid:col===T.gold?T.goldMid:T.greenMid,marginBottom:6}}>{banner.headline}</div>
      {issues.map((t,i)=><div key={i} style={{fontSize:12,color:T.textMid,display:"flex",gap:8,alignItems:"flex-start",marginBottom:3}}><span style={{color:col,flexShrink:0}}>▸</span>{t}</div>)}
      {wins.length>0&&<div style={{display:"flex",gap:12,flexWrap:"wrap",marginTop:wins.length&&issues.length?8:0}}>{wins.map((t,i)=><div key={i} style={{fontSize:11,color:T.green,display:"flex",gap:5}}><span>✓</span>{t}</div>)}</div>}
    </div>
  );
}

function MetricCard({ icon, title, status, children }) {
  const col=statusColor(status); const pale=statusPale(status);
  return (
    <div style={{background:T.bgCard,borderRadius:18,border:`1.5px solid ${T.border}`,borderTop:`4px solid ${col}`,padding:"18px 20px",boxShadow:`0 2px 12px ${T.shadow}`}}>
      <div style={{display:"flex",alignItems:"center",gap:9,marginBottom:14}}>
        <div style={{width:34,height:34,borderRadius:10,background:pale,border:`1.5px solid ${col}33`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:17,flexShrink:0}}>{icon}</div>
        <span style={{fontSize:13,fontWeight:800,color:T.textMid,textTransform:"uppercase",letterSpacing:0.8}}>{title}</span>
        <div style={{marginLeft:"auto",width:8,height:8,borderRadius:"50%",background:col,boxShadow:`0 0 8px ${col}88`,flexShrink:0}}/>
      </div>
      {children}
    </div>
  );
}

function MiniStat({ label, val, status }) {
  return (
    <div style={{background:T.bgDeep,borderRadius:10,padding:"9px 11px",border:`1px solid ${T.border}55`}}>
      <div style={{fontSize:10,color:T.textLight,marginBottom:3,fontWeight:600}}>{label}</div>
      <div style={{fontSize:15,fontWeight:800,color:status?statusColor(status):T.textDark}}>{val}</div>
    </div>
  );
}

function Spinner() {
  return <div style={{width:32,height:32,border:`3px solid ${T.border}`,borderTop:`3px solid ${T.greenMid}`,borderRadius:"50%",animation:"spin 0.8s linear infinite"}} />;
}

/* ═══════════════════════════════════════════════════════════════════
   WIZARD STEP COMPONENTS
═══════════════════════════════════════════════════════════════════ */

// Step 1 — Cash
function StepCash({ data, onChange }) {
  return (
    <div style={{display:"flex",flexDirection:"column",gap:16}}>
      <div style={{fontSize:13,color:T.textSoft,lineHeight:1.6,background:T.greenPale,borderRadius:10,padding:"10px 14px",border:`1px solid ${T.green}33`}}>
        💡 Open your bank account and enter what you see right now. This is the most important number in the whole dashboard.
      </div>
      {[
        {label:"Cash in the bank right now",key:"starting_cash",prefix:"$",type:"number",placeholder:"2100"},
        {label:"Your monthly take-home pay (owner draw)",key:"owner_draw_monthly",prefix:"$",type:"number",placeholder:"3000"},
        {label:"Fixed monthly costs (rent, software, insurance, phone)",key:"fixed_monthly_expenses",prefix:"$",type:"number",placeholder:"450"},
        {label:"Variable monthly costs (materials, marketing, etc.)",key:"variable_monthly_expenses",prefix:"$",type:"number",placeholder:"100"},
      ].map(({label,key,prefix,type,placeholder})=>(
        <div key={key}>
          <label style={{fontSize:12,fontWeight:700,color:T.textMid,display:"block",marginBottom:6}}>{label}</label>
          <div style={{display:"flex",alignItems:"center",background:T.bgCard,border:`2px solid ${T.border}`,borderRadius:12,overflow:"hidden"}}>
            {prefix&&<span style={{padding:"0 12px",fontSize:16,color:T.textSoft,fontWeight:700,background:T.bgDeep,alignSelf:"stretch",display:"flex",alignItems:"center"}}>{prefix}</span>}
            <input type={type} placeholder={placeholder} value={data[key]||""}
              onChange={e=>onChange(key,type==="number"?+e.target.value:e.target.value)}
              style={{flex:1,padding:"12px 14px",fontSize:15,fontWeight:700,background:"transparent",border:"none",outline:"none",fontFamily:"'Playfair Display',serif",color:T.textDark}}/>
          </div>
        </div>
      ))}
    </div>
  );
}

// Step 2 — Active Projects
function StepProjects({ projects, onUpdate, onAdd, onRemove }) {
  const statusOptions = ["Active","On Hold","Completed"];
  return (
    <div style={{display:"flex",flexDirection:"column",gap:14}}>
      <div style={{fontSize:13,color:T.textSoft,lineHeight:1.6,background:T.bluePale,borderRadius:10,padding:"10px 14px",border:`1px solid ${T.blue}33`}}>
        💡 List every project you're currently working on or have on hold. The hours remaining drive your backlog and delay calculations.
      </div>
      {projects.map((p,idx)=>(
        <div key={p.id} style={{background:T.bgCard,border:`1.5px solid ${T.border}`,borderRadius:14,padding:"14px 16px"}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:12}}>
            <span style={{fontSize:12,fontWeight:800,color:T.textMid}}>Project {idx+1}</span>
            <button onClick={()=>onRemove(p.id)} style={{background:T.redPale,border:`1px solid ${T.red}44`,color:T.red,borderRadius:8,padding:"4px 10px",fontSize:11,cursor:"pointer",fontFamily:"inherit",fontWeight:700}}>Remove</button>
          </div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
            {[
              {label:"Client name",key:"client",placeholder:"Hartwell Construction"},
              {label:"Project name",key:"name",placeholder:"Site Analysis"},
            ].map(({label,key,placeholder})=>(
              <div key={key}>
                <label style={{fontSize:11,fontWeight:700,color:T.textMid,display:"block",marginBottom:4}}>{label}</label>
                <input value={p[key]||""} placeholder={placeholder}
                  onChange={e=>onUpdate(p.id,key,e.target.value)}
                  style={{width:"100%",padding:"10px 12px",background:T.bgDeep,border:`1.5px solid ${T.border}`,borderRadius:10,fontSize:13,fontWeight:600,color:T.textDark,outline:"none",fontFamily:"inherit",boxSizing:"border-box"}}/>
              </div>
            ))}
            <div>
              <label style={{fontSize:11,fontWeight:700,color:T.textMid,display:"block",marginBottom:4}}>Hours remaining</label>
              <input type="number" value={p.hrs_remaining||""} placeholder="20"
                onChange={e=>onUpdate(p.id,"hrs_remaining",+e.target.value)}
                style={{width:"100%",padding:"10px 12px",background:T.bgDeep,border:`1.5px solid ${T.border}`,borderRadius:10,fontSize:13,fontWeight:700,color:T.textDark,outline:"none",fontFamily:"'Playfair Display',serif",boxSizing:"border-box"}}/>
            </div>
            <div>
              <label style={{fontSize:11,fontWeight:700,color:T.textMid,display:"block",marginBottom:4}}>Billing rate ($/hr)</label>
              <input type="number" value={p.billing_rate||""} placeholder="95"
                onChange={e=>onUpdate(p.id,"billing_rate",+e.target.value)}
                style={{width:"100%",padding:"10px 12px",background:T.bgDeep,border:`1.5px solid ${T.border}`,borderRadius:10,fontSize:13,fontWeight:700,color:T.textDark,outline:"none",fontFamily:"'Playfair Display',serif",boxSizing:"border-box"}}/>
            </div>
            <div style={{gridColumn:"span 2"}}>
              <label style={{fontSize:11,fontWeight:700,color:T.textMid,display:"block",marginBottom:4}}>Status</label>
              <div style={{display:"flex",gap:8}}>
                {statusOptions.map(s=>(
                  <button key={s} onClick={()=>onUpdate(p.id,"status",s)}
                    style={{flex:1,padding:"8px",borderRadius:8,border:`1.5px solid ${p.status===s?T.greenMid:T.border}`,
                      background:p.status===s?T.greenPale:T.bgDeep,color:p.status===s?T.green:T.textSoft,
                      fontWeight:700,fontSize:11,cursor:"pointer",fontFamily:"inherit",transition:"all 0.2s"}}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      ))}
      <button onClick={onAdd}
        style={{background:"transparent",border:`2px dashed ${T.borderMid}`,borderRadius:14,padding:"14px",
          color:T.textSoft,fontSize:13,fontWeight:700,cursor:"pointer",fontFamily:"inherit",
          transition:"all 0.2s",display:"flex",alignItems:"center",justifyContent:"center",gap:8}}
        onMouseEnter={e=>{e.currentTarget.style.borderColor=T.greenMid;e.currentTarget.style.color=T.green;}}
        onMouseLeave={e=>{e.currentTarget.style.borderColor=T.borderMid;e.currentTarget.style.color=T.textSoft;}}>
        + Add Another Project
      </button>
    </div>
  );
}

// Step 3 — Team
function StepTeam({ data, onChange }) {
  return (
    <div style={{display:"flex",flexDirection:"column",gap:16}}>
      <div style={{fontSize:13,color:T.textSoft,lineHeight:1.6,background:T.goldPale,borderRadius:10,padding:"10px 14px",border:`1px solid ${T.gold}33`}}>
        💡 This tells the engine how much work you can actually handle each week. Be honest about admin time — email, scheduling, and bookkeeping eat more hours than people think.
      </div>
      {[
        {label:"Your total available hours per week",key:"owner_total_hours_week",type:"number",suffix:"hrs/wk",placeholder:"20"},
        {label:"Admin hours per week (email, scheduling, bookkeeping)",key:"admin_hours_week",type:"number",suffix:"hrs/wk",placeholder:"6"},
        {label:"Your hourly billing rate",key:"base_hourly_rate",type:"number",prefix:"$",placeholder:"95"},
        {label:"Active subcontractors / helpers right now",key:"num_subcontractors",type:"number",suffix:"people",placeholder:"0"},
      ].map(({label,key,type,prefix,suffix,placeholder})=>(
        <div key={key}>
          <label style={{fontSize:12,fontWeight:700,color:T.textMid,display:"block",marginBottom:6}}>{label}</label>
          <div style={{display:"flex",alignItems:"center",background:T.bgCard,border:`2px solid ${T.border}`,borderRadius:12,overflow:"hidden"}}>
            {prefix&&<span style={{padding:"0 12px",fontSize:15,color:T.textSoft,fontWeight:700,background:T.bgDeep,alignSelf:"stretch",display:"flex",alignItems:"center"}}>{prefix}</span>}
            <input type={type} placeholder={placeholder} value={data[key]||""}
              onChange={e=>onChange(key,+e.target.value)}
              style={{flex:1,padding:"12px 14px",fontSize:15,fontWeight:700,background:"transparent",border:"none",outline:"none",fontFamily:"'Playfair Display',serif",color:T.textDark}}/>
            {suffix&&<span style={{padding:"0 12px",fontSize:12,color:T.textLight,background:T.bgDeep,alignSelf:"stretch",display:"flex",alignItems:"center"}}>{suffix}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

// Step 4 — Leads & Clients
function StepLeads({ data, onChange }) {
  return (
    <div style={{display:"flex",flexDirection:"column",gap:16}}>
      <div style={{fontSize:13,color:T.textSoft,lineHeight:1.6,background:T.greenPale,borderRadius:10,padding:"10px 14px",border:`1px solid ${T.green}33`}}>
        💡 Think about last week — how many people reached out or asked about your services? Regular clients are people who pay you a set amount every month regardless of projects.
      </div>
      {[
        {label:"Interested people reaching out per week (average)",key:"base_leads_per_week",type:"number",suffix:"people/wk",placeholder:"2"},
        {label:"Current regular / retainer clients",key:"current_retainer_clients",type:"number",suffix:"clients",placeholder:"0"},
        {label:"What each regular client pays per month",key:"avg_retainer_value_monthly",type:"number",prefix:"$",suffix:"/mo",placeholder:"800"},
        {label:"Current month (1–12)",key:"current_month",type:"number",suffix:"month",placeholder:"3"},
      ].map(({label,key,type,prefix,suffix,placeholder})=>(
        <div key={key}>
          <label style={{fontSize:12,fontWeight:700,color:T.textMid,display:"block",marginBottom:6}}>{label}</label>
          <div style={{display:"flex",alignItems:"center",background:T.bgCard,border:`2px solid ${T.border}`,borderRadius:12,overflow:"hidden"}}>
            {prefix&&<span style={{padding:"0 12px",fontSize:15,color:T.textSoft,fontWeight:700,background:T.bgDeep,alignSelf:"stretch",display:"flex",alignItems:"center"}}>{prefix}</span>}
            <input type={type} placeholder={placeholder} value={data[key]||""}
              onChange={e=>onChange(key,type==="number"?+e.target.value:e.target.value)}
              style={{flex:1,padding:"12px 14px",fontSize:15,fontWeight:700,background:"transparent",border:"none",outline:"none",fontFamily:"'Playfair Display',serif",color:T.textDark}}/>
            {suffix&&<span style={{padding:"0 12px",fontSize:12,color:T.textLight,background:T.bgDeep,alignSelf:"stretch",display:"flex",alignItems:"center"}}>{suffix}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

// Step 5 — Review & Save
function StepReview({ formData, projects, isSaving, saveResult }) {
  const totalHrs = projects.filter(p=>p.status!=="Completed").reduce((s,p)=>s+(p.hrs_remaining||0),0);
  const totalMrr = (formData.current_retainer_clients||0)*(formData.avg_retainer_value_monthly||800);
  const weeksLeft = (formData.starting_cash||0)/((formData.fixed_monthly_expenses||450)+(formData.variable_monthly_expenses||100)+(formData.owner_draw_monthly||3000))*4.33/4.33;

  return (
    <div style={{display:"flex",flexDirection:"column",gap:14}}>
      {saveResult==="success"&&(
        <div style={{background:T.greenPale,border:`2px solid ${T.green}44`,borderRadius:12,padding:"14px 18px",fontSize:13,color:T.green,fontWeight:700,display:"flex",gap:10,alignItems:"center"}}>
          ✅ Saved! Dashboard is updating with your new numbers.
        </div>
      )}
      {saveResult==="error"&&(
        <div style={{background:T.redPale,border:`2px solid ${T.red}44`,borderRadius:12,padding:"14px 18px",fontSize:13,color:T.red,fontWeight:700}}>
          ⚠️ Could not save right now. Check your connection and try again.
        </div>
      )}
      <div style={{fontSize:13,color:T.textSoft,lineHeight:1.5}}>Here's a summary of what you entered. If anything looks off, go back and fix it before saving.</div>
      {[
        {label:"💵 Cash on hand",      val:`$${(formData.starting_cash||0).toLocaleString()}`},
        {label:"📤 Monthly going out", val:`$${((formData.fixed_monthly_expenses||0)+(formData.variable_monthly_expenses||0)+(formData.owner_draw_monthly||0)).toLocaleString()}/mo`},
        {label:"⏱️ Active project hours", val:`${totalHrs} hrs across ${projects.filter(p=>p.status!=="Completed").length} projects`},
        {label:"⚡ Your weekly capacity", val:`${((formData.owner_total_hours_week||20)-(formData.admin_hours_week||6))*0.85} hrs/wk sustainable`},
        {label:"📣 Leads per week",     val:`${formData.base_leads_per_week||2} people/wk`},
        {label:"📅 Regular clients",    val:`${formData.current_retainer_clients||0} clients · $${totalMrr.toLocaleString()}/mo`},
        {label:"💲 Billing rate",       val:`$${formData.base_hourly_rate||95}/hr`},
        {label:"👷 Helpers hired",      val:`${formData.num_subcontractors||0}`},
      ].map(({label,val})=>(
        <div key={label} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"10px 14px",background:T.bgCard,borderRadius:10,border:`1px solid ${T.border}`}}>
          <span style={{fontSize:12,color:T.textMid,fontWeight:600}}>{label}</span>
          <span style={{fontSize:14,fontWeight:800,color:T.textDark,fontFamily:"'Playfair Display',serif"}}>{val}</span>
        </div>
      ))}
      {isSaving&&(
        <div style={{display:"flex",alignItems:"center",gap:12,padding:"12px 16px",background:T.bgDeep,borderRadius:10}}>
          <Spinner/>
          <span style={{fontSize:13,color:T.textMid,fontWeight:600}}>Saving to Dataverse...</span>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   WEEKLY CHECK-IN WIZARD
═══════════════════════════════════════════════════════════════════ */
const WIZARD_STEPS = [
  { id:"cash",     icon:"💵", title:"Money",         subtitle:"Cash on hand + expenses" },
  { id:"projects", icon:"📋", title:"Active Work",   subtitle:"Projects + hours remaining" },
  { id:"team",     icon:"👷", title:"Your Team",     subtitle:"Hours, rate, helpers" },
  { id:"leads",    icon:"📣", title:"Leads & Clients",subtitle:"New business + regulars" },
  { id:"review",   icon:"✅", title:"Review & Save", subtitle:"Double-check and submit" },
];

function WeeklyWizard({ onClose, onSaved, initialData }) {
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState({
    starting_cash:              initialData?.cash?.amount             || 2100,
    owner_draw_monthly:         3000,
    fixed_monthly_expenses:     450,
    variable_monthly_expenses:  100,
    owner_total_hours_week:     20,
    admin_hours_week:           6,
    base_hourly_rate:           95,
    num_subcontractors:         0,
    base_leads_per_week:        2,
    current_retainer_clients:   0,
    avg_retainer_value_monthly: 800,
    current_month:              new Date().getMonth()+1,
  });
  const [projects, setProjects] = useState(MOCK_PROJECTS);
  const [isSaving, setIsSaving] = useState(false);
  const [saveResult, setSaveResult] = useState(null);

  const updateField = useCallback((k,v) => setFormData(d=>({...d,[k]:v})), []);
  const updateProject = useCallback((id,k,v) => setProjects(ps=>ps.map(p=>p.id===id?{...p,[k]:v}:p)), []);
  const addProject = useCallback(() => setProjects(ps=>[...ps,{id:Date.now(),code:`P-${String(ps.length+1).padStart(3,"0")}`,client:"",name:"",hrs_remaining:0,billing_rate:95,status:"Active"}]), []);
  const removeProject = useCallback((id) => setProjects(ps=>ps.filter(p=>p.id!==id)), []);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveResult(null);
    try {
      const activeHrs = projects.filter(p=>p.status!=="Completed").reduce((s,p)=>s+(p.hrs_remaining||0),0);
      const payload = {
        ...formData,
        active_workload_hrs: activeHrs,
        num_active_projects: projects.filter(p=>p.status!=="Completed").length,
      };
      await apiFetch("/update-inputs", { method:"POST", body:JSON.stringify(payload) });
      setSaveResult("success");
      setTimeout(() => onSaved(), 1800);
    } catch {
      setSaveResult("error");
    } finally {
      setIsSaving(false);
    }
  };

  const canAdvance = () => {
    if (step===0) return (formData.starting_cash||0)>0;
    if (step===1) return projects.length>0;
    return true;
  };

  return (
    <div style={{position:"fixed",inset:0,background:"rgba(28,43,30,0.55)",zIndex:100,display:"flex",alignItems:"center",justifyContent:"center",padding:20,backdropFilter:"blur(4px)"}}>
      <div style={{background:T.bgCard,borderRadius:24,width:"100%",maxWidth:560,maxHeight:"90vh",display:"flex",flexDirection:"column",boxShadow:`0 24px 64px ${T.shadowMd}`,overflow:"hidden"}}>

        {/* Header */}
        <div style={{background:T.bgDark,padding:"18px 24px",display:"flex",justifyContent:"space-between",alignItems:"center",flexShrink:0}}>
          <div>
            <div style={{fontSize:16,fontWeight:900,color:T.white,fontFamily:"'Playfair Display',serif"}}>Weekly Check-In</div>
            <div style={{fontSize:11,color:"#6a8a6e",marginTop:2}}>Update your numbers · {new Date().toLocaleDateString("en-US",{month:"long",day:"numeric",year:"numeric"})}</div>
          </div>
          <button onClick={onClose} style={{background:"#1a2a1c",border:`1px solid ${T.borderDark}`,color:"#6a8a6e",width:32,height:32,borderRadius:8,cursor:"pointer",fontSize:16,display:"flex",alignItems:"center",justifyContent:"center"}}>✕</button>
        </div>

        {/* Step progress */}
        <div style={{padding:"14px 24px",borderBottom:`1px solid ${T.border}`,background:T.bg,flexShrink:0}}>
          <div style={{display:"flex",gap:6}}>
            {WIZARD_STEPS.map((s,i)=>{
              const done=i<step; const active=i===step;
              return (
                <div key={s.id} style={{flex:1,display:"flex",flexDirection:"column",alignItems:"center",gap:4,cursor:done?"pointer":"default"}}
                  onClick={()=>done&&setStep(i)}>
                  <div style={{width:32,height:32,borderRadius:10,
                    background:done?T.green:active?T.greenPale:T.bgDeep,
                    border:`2px solid ${done||active?T.green:T.border}`,
                    display:"flex",alignItems:"center",justifyContent:"center",
                    fontSize:done?14:16,fontWeight:700,color:done?T.white:active?T.green:T.textLight,
                    transition:"all 0.3s"}}>
                    {done?"✓":s.icon}
                  </div>
                  <div style={{fontSize:9,color:active?T.green:done?T.greenMid:T.textLight,fontWeight:active||done?700:400,textAlign:"center",lineHeight:1.2}}>{s.title}</div>
                </div>
              );
            })}
          </div>
          <div style={{marginTop:10,height:3,background:T.bgDeep,borderRadius:3,overflow:"hidden"}}>
            <div style={{height:"100%",width:`${(step/(WIZARD_STEPS.length-1))*100}%`,background:`linear-gradient(90deg,${T.greenMid},${T.greenLight})`,borderRadius:3,transition:"width 0.4s ease"}}/>
          </div>
        </div>

        {/* Step content */}
        <div style={{flex:1,overflow:"auto",padding:"20px 24px"}}>
          <div style={{marginBottom:16}}>
            <div style={{fontSize:17,fontWeight:800,color:T.textDark,fontFamily:"'Playfair Display',serif"}}>{WIZARD_STEPS[step].title}</div>
            <div style={{fontSize:12,color:T.textLight,marginTop:2}}>{WIZARD_STEPS[step].subtitle}</div>
          </div>
          {step===0 && <StepCash data={formData} onChange={updateField}/>}
          {step===1 && <StepProjects projects={projects} onUpdate={updateProject} onAdd={addProject} onRemove={removeProject}/>}
          {step===2 && <StepTeam data={formData} onChange={updateField}/>}
          {step===3 && <StepLeads data={formData} onChange={updateField}/>}
          {step===4 && <StepReview formData={formData} projects={projects} isSaving={isSaving} saveResult={saveResult}/>}
        </div>

        {/* Footer nav */}
        <div style={{padding:"14px 24px",borderTop:`1px solid ${T.border}`,display:"flex",justifyContent:"space-between",flexShrink:0,background:T.bg}}>
          <button onClick={()=>step>0&&setStep(s=>s-1)} disabled={step===0}
            style={{padding:"10px 20px",borderRadius:10,border:`1.5px solid ${T.border}`,background:"transparent",color:step===0?T.textLight:T.textMid,fontSize:13,fontWeight:700,cursor:step===0?"default":"pointer",fontFamily:"inherit",opacity:step===0?0.4:1}}>
            ← Back
          </button>
          <span style={{fontSize:11,color:T.textLight,alignSelf:"center"}}>Step {step+1} of {WIZARD_STEPS.length}</span>
          {step<WIZARD_STEPS.length-1?(
            <button onClick={()=>canAdvance()&&setStep(s=>s+1)} disabled={!canAdvance()}
              style={{padding:"10px 24px",borderRadius:10,border:"none",background:canAdvance()?T.green:"#ccc",color:T.white,fontSize:13,fontWeight:700,cursor:canAdvance()?"pointer":"default",fontFamily:"inherit",boxShadow:canAdvance()?`0 4px 12px ${T.green}44`:"none",transition:"all 0.2s"}}>
              Next →
            </button>
          ):(
            <button onClick={handleSave} disabled={isSaving||saveResult==="success"}
              style={{padding:"10px 24px",borderRadius:10,border:"none",background:saveResult==="success"?T.green:T.gold,color:T.white,fontSize:13,fontWeight:700,cursor:isSaving?"wait":"pointer",fontFamily:"inherit",boxShadow:`0 4px 12px ${T.gold}44`,transition:"all 0.2s",display:"flex",alignItems:"center",gap:8}}>
              {isSaving?"Saving...":saveResult==="success"?"✓ Saved!":"💾 Save to Dashboard"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   PREDICTION PANEL (inline, not a separate file)
═══════════════════════════════════════════════════════════════════ */
const DEFAULT_SLIDERS = { moreLeads:2.4, raiseRate:95, ownerPay:3500, hireHelp:0, addRegulars:0 };

function PredictionPanel({ liveData }) {
  const [sliders, setSliders] = useState(DEFAULT_SLIDERS);
  const [pred, setPred] = useState(null);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef(null);

  const set = (k,v) => setSliders(s=>({...s,[k]:v}));
  const changed = JSON.stringify(sliders)!==JSON.stringify(DEFAULT_SLIDERS);

  // Debounced predict call
  useEffect(()=>{
    if(debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async()=>{
      setLoading(true);
      try {
        const res = await apiFetch("/predict",{method:"POST",body:JSON.stringify({
          base_leads_per_week: sliders.moreLeads,
          base_hourly_rate: sliders.raiseRate,
          owner_draw_monthly: sliders.ownerPay,
          num_subcontractors: sliders.hireHelp,
          current_retainer_clients: sliders.addRegulars,
        })});
        setPred(res);
      } catch(e) { console.error(e); }
      finally { setLoading(false); }
    }, 400);
  }, [sliders]);

  const live = liveData;
  const p = pred?.predicted || live;
  const d = pred?.deltas || {};

  const Delta = ({val, invert=false}) => {
    if(!val||Math.abs(val)<0.5) return null;
    const good = invert?(val<0):(val>0);
    return <span style={{fontSize:10,fontWeight:700,color:good?T.green:T.red,background:good?T.greenPale:T.redPale,border:`1px solid ${good?T.green:T.red}44`,borderRadius:5,padding:"1px 6px",marginLeft:6}}>{val>0?"+":""}{typeof val==="number"?val.toFixed(0):val}</span>;
  };

  const Slider = ({label,detail,k,min,max,step,prefix="",suffix="",warn}) => (
    <div style={{background:T.bgCard,border:`1.5px solid ${warn?T.gold+"88":T.border}`,borderRadius:14,padding:"13px 15px",boxShadow:warn?`0 0 0 3px ${T.goldPale}`:`0 2px 8px ${T.shadow}`,transition:"all 0.25s"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:8,gap:12}}>
        <div style={{flex:1}}>
          <div style={{fontSize:13,fontWeight:800,color:T.textDark}}>{label}</div>
          {detail&&<div style={{fontSize:10,color:T.textLight,marginTop:1}}>{detail}</div>}
        </div>
        <div style={{fontSize:16,fontWeight:900,color:T.bgDark,background:T.goldPale,border:`1.5px solid ${T.goldMid}66`,borderRadius:10,padding:"3px 12px",minWidth:60,textAlign:"center",fontFamily:"'Playfair Display',serif"}}>
          {prefix}{typeof sliders[k]==="number"&&sliders[k]>999?sliders[k].toLocaleString():sliders[k]}{suffix}
        </div>
      </div>
      <input type="range" min={min} max={max} step={step} value={sliders[k]} onChange={e=>set(k,+e.target.value)}
        style={{width:"100%",accentColor:T.greenMid,cursor:"pointer"}}/>
      {warn&&<div style={{marginTop:8,fontSize:11,color:T.gold,background:T.goldPale,border:`1px solid ${T.gold}55`,borderRadius:8,padding:"5px 9px"}}>⚠️ {warn}</div>}
    </div>
  );

  const CmpRow = ({label,lv,pv,fmt=v=>v,inv=false}) => {
    const diff=pv-lv; const chg=Math.abs(diff)>=0.5;
    const good=chg?((diff>0)!==inv):false; const col=good?T.green:T.red;
    const sign=diff>0?"+":"";
    return (
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"7px 0",borderBottom:`1px solid ${T.border}55`}}>
        <span style={{fontSize:12,color:T.textSoft,flex:1}}>{label}</span>
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          <span style={{fontSize:11,color:T.textLight,textDecoration:chg?"line-through":"none"}}>{fmt(lv)}</span>
          {chg&&<><span style={{fontSize:10,color:T.textLight}}>→</span><span style={{fontSize:13,fontWeight:800,color:col}}>{fmt(pv)}</span><span style={{fontSize:10,fontWeight:700,color:col,background:good?T.greenPale:T.redPale,border:`1px solid ${col}44`,borderRadius:5,padding:"1px 6px"}}>{sign}{fmt(diff)}</span></>}
          {!chg&&<span style={{fontSize:12,fontWeight:700,color:T.textDark}}>{fmt(pv)}</span>}
        </div>
      </div>
    );
  };

  const warn = {
    moreLeads: sliders.moreLeads>3.5&&sliders.hireHelp===0?"More leads without help will make your backlog worse.":null,
    ownerPay:  sliders.ownerPay>4500&&(p?.cash?.ending_cash||0)<2000?"This pay level will drain your savings.":null,
    hireHelp:  sliders.moreLeads>4&&sliders.hireHelp===0?"At this many leads you'll need help.":null,
  };

  return (
    <div style={{display:"flex",flexDirection:"column",height:"calc(100vh - 66px)",overflow:"hidden"}}>
      {/* Locked current strip */}
      <div style={{background:T.bgDark,borderBottom:`3px solid ${T.greenMid}`,padding:"12px 28px",flexShrink:0}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
          <span style={{fontSize:11,fontWeight:700,color:T.greenLight,textTransform:"uppercase",letterSpacing:1.5}}>📍 Where you are right now — this doesn't change</span>
          <span style={{fontSize:10,color:"#4a6a4e"}}>JD Analytics & Solutions · Adjust sliders below to test ideas</span>
        </div>
        <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10}}>
          {[
            {icon:"💵",label:"Money in the bank",     val:`$${(live?.cash?.amount||0).toLocaleString()}`,      col:T.redLight},
            {icon:"📋",label:"Work piled up",          val:`${live?.workload?.active_hrs||0} hrs`,              col:T.redLight},
            {icon:"🔧",label:"Win rate",               val:`${Math.round((live?.pipeline?.win_rate||0)*100)}%`, col:T.goldLight},
            {icon:"😊",label:"Customer happiness",     val:`${live?.quality?.score||0} / 100`,                  col:T.goldLight},
          ].map(({icon,label,val,col})=>(
            <div key={label} style={{background:"#1a2a1c",border:`1px solid ${T.borderDark}`,borderRadius:12,padding:"10px 14px"}}>
              <div style={{fontSize:10,color:"#4a6a4e",marginBottom:4,fontWeight:600}}>{icon} {label}</div>
              <div style={{fontSize:18,fontWeight:900,color:col,fontFamily:"'Playfair Display',serif",lineHeight:1.1}}>{val}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Scrollable lab */}
      <div style={{flex:1,overflow:"auto",padding:"20px 28px",background:T.bg}}>
        <div style={{display:"grid",gridTemplateColumns:"300px 1fr",gap:22,alignItems:"start"}}>
          {/* Sliders */}
          <div style={{display:"flex",flexDirection:"column",gap:10}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:4}}>
              <span style={{fontSize:14,fontWeight:800,color:T.textDark}}>🎮 What if I...</span>
              {changed&&<button onClick={()=>setSliders(DEFAULT_SLIDERS)} style={{background:T.bgCard,border:`1.5px solid ${T.borderMid}`,color:T.textSoft,fontSize:11,padding:"5px 12px",borderRadius:8,cursor:"pointer",fontFamily:"inherit",fontWeight:700}}>↺ Reset</button>}
            </div>
            <Slider label="...got more people interested?" detail="Potential customers per week" k="moreLeads" min={0} max={10} step={0.5} warn={warn.moreLeads}/>
            <Slider label="...charged more per hour?" detail="Currently $95/hr" k="raiseRate" min={60} max={200} step={5} prefix="$"/>
            <Slider label="...paid myself less for now?" detail="Current take-home: $3,500/mo" k="ownerPay" min={0} max={8000} step={250} prefix="$" suffix="/mo" warn={warn.ownerPay}/>
            <Slider label="...hired a helper?" detail="Each adds ~20 billable hrs/week" k="hireHelp" min={0} max={4} step={1} suffix={` helper${sliders.hireHelp!==1?"s":""}`} warn={warn.hireHelp}/>
            <Slider label="...signed regular monthly clients?" detail="Each pays ~$800/month" k="addRegulars" min={0} max={8} step={1} suffix={` client${sliders.addRegulars!==1?"s":""}`}/>
            {loading&&<div style={{display:"flex",alignItems:"center",gap:10,padding:"10px 14px",background:T.bgDeep,borderRadius:10,fontSize:12,color:T.textMid}}><Spinner/>Recalculating...</div>}
          </div>

          {/* Results */}
          <div style={{display:"flex",flexDirection:"column",gap:14}}>
            {/* Score */}
            <div style={{background:T.bgCard,border:`1.5px solid ${T.border}`,borderRadius:18,padding:"18px 22px",boxShadow:`0 2px 12px ${T.shadow}`}}>
              <div style={{fontSize:12,fontWeight:800,color:T.textMid,textTransform:"uppercase",letterSpacing:0.8,marginBottom:14}}>Business Score — Before vs After</div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:24}}>
                <div><div style={{fontSize:11,color:T.textLight,marginBottom:8,fontWeight:600}}>Right now</div><XPStrip xp={live?.score?.xp||5}/></div>
                <div><div style={{fontSize:11,color:T.textLight,marginBottom:8,fontWeight:600}}>With your changes</div><XPStrip xp={p?.score?.xp||5}/></div>
              </div>
              {(p?.score?.xp||5)>(live?.score?.xp||5)&&<div style={{marginTop:12,background:T.greenPale,border:`1px solid ${T.green}44`,borderRadius:10,padding:"8px 14px",fontSize:12,color:T.green,fontWeight:700}}>🌱 +{(p?.score?.xp||5)-(live?.score?.xp||5)} point improvement</div>}
            </div>

            {/* 4 compare blocks */}
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
              {[
                {icon:"💵",title:"Money",rows:[
                  {label:"Cash after 3 months",  lv:live?.cash?.net_12w||0,     pv:p?.cash?.net_12w||0,     fmt:v=>`$${Math.round(v).toLocaleString()}`},
                  {label:"Coming in / week",      lv:live?.cash?.weekly_in||0,   pv:p?.cash?.weekly_in||0,   fmt:v=>`$${Math.round(v).toLocaleString()}`},
                  {label:"Going out / week",      lv:live?.cash?.weekly_out||0,  pv:p?.cash?.weekly_out||0,  fmt:v=>`$${Math.round(v).toLocaleString()}`,inv:true},
                ]},
                {icon:"📋",title:"Workload",rows:[
                  {label:"Hours piled up",        lv:live?.workload?.backlog_hrs||0, pv:p?.workload?.backlog_hrs||0, fmt:v=>`${Math.round(v)}h`,inv:true},
                  {label:"Customer wait",         lv:live?.workload?.wait_days||0,   pv:p?.workload?.wait_days||0,   fmt:v=>`${Math.round(v)} days`,inv:true},
                  {label:"How slammed",           lv:live?.workload?.stress_score||0,pv:p?.workload?.stress_score||0,fmt:v=>`${Math.round(v)}%`,inv:true},
                ]},
                {icon:"🔧",title:"Jobs",rows:[
                  {label:"Jobs won / week",       lv:live?.pipeline?.closes_12w/12||0,    pv:p?.pipeline?.closes_12w/12||0,    fmt:v=>v.toFixed(2)},
                  {label:"Revenue (3 mo.)",       lv:live?.pipeline?.revenue_12w||0,       pv:p?.pipeline?.revenue_12w||0,       fmt:v=>`$${Math.round(v).toLocaleString()}`},
                  {label:"Avg job size",          lv:live?.pipeline?.avg_project_value||0, pv:p?.pipeline?.avg_project_value||0, fmt:v=>`$${Math.round(v).toLocaleString()}`},
                ]},
                {icon:"😊",title:"Customers",rows:[
                  {label:"Happiness score",       lv:live?.quality?.score||0,              pv:p?.quality?.score||0,              fmt:v=>`${Math.round(v)}/100`},
                  {label:"Will come back",        lv:(live?.quality?.retention_likelihood||0)*100, pv:(p?.quality?.retention_likelihood||0)*100, fmt:v=>`${Math.round(v)}%`},
                  {label:"Monthly recurring",     lv:live?.recurring?.mrr||0,              pv:p?.recurring?.mrr||0,              fmt:v=>`$${Math.round(v).toLocaleString()}`},
                ]},
              ].map(({icon,title,rows})=>(
                <div key={title} style={{background:T.bgCard,border:`1.5px solid ${T.border}`,borderRadius:14,padding:"14px 18px",boxShadow:`0 2px 8px ${T.shadow}`}}>
                  <div style={{fontSize:12,fontWeight:800,color:T.textMid,marginBottom:10,display:"flex",alignItems:"center",gap:7}}><span>{icon}</span>{title}</div>
                  {rows.map(r=><CmpRow key={r.label} label={r.label} lv={r.lv} pv={r.pv} fmt={r.fmt} inv={r.inv}/>)}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   MAIN DASHBOARD
═══════════════════════════════════════════════════════════════════ */
export default function Dashboard() {
  const [mode, setMode]           = useState("snapshot");
  const [data, setData]           = useState(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [showWizard, setShowWizard] = useState(false);
  const [pulse, setPulse]         = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [newBadge, setNewBadge]   = useState(null);
  const prevBadges                = useRef({});

  const loadDashboard = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await apiFetch("/dashboard");
      // Badge unlock detection
      if (res.badges && prevBadges.current) {
        const fresh = Object.entries(res.badges).filter(([k,v])=>v&&!prevBadges.current[k]);
        if (fresh.length) {
          const a = ACHIEVEMENTS.find(a=>a.id===fresh[0][0]);
          if (a) { setNewBadge(a); setTimeout(()=>setNewBadge(null),3500); }
        }
      }
      prevBadges.current = res.badges||{};
      setData(res);
      setLastUpdated(new Date());
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(()=>{ loadDashboard(); }, []);
  useEffect(()=>{ const t=setInterval(()=>setPulse(p=>!p),2400); return()=>clearInterval(t); },[]);

  const d = data || MOCK_DASHBOARD;

  return (
    <div style={{minHeight:"100vh",background:T.bg,fontFamily:"'DM Sans',system-ui,sans-serif",color:T.textDark}}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@700;900&display=swap');
        *{box-sizing:border-box;margin:0;padding:0;}
        input[type=range]{-webkit-appearance:none;height:6px;border-radius:3px;background:${T.bgDeep};outline:none;}
        input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;border-radius:50%;background:${T.bgDark};cursor:pointer;border:3px solid ${T.greenGlow};box-shadow:0 2px 6px ${T.shadowMd};}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes toastIn{from{transform:translateX(110%);opacity:0}to{transform:translateX(0);opacity:1}}
        @keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
      `}</style>

      {/* Badge toast */}
      {newBadge&&(
        <div style={{position:"fixed",top:80,right:24,zIndex:200,background:T.bgDark,color:T.white,borderRadius:16,padding:"14px 20px",boxShadow:`0 12px 32px ${T.shadowMd}`,border:`1.5px solid ${T.goldMid}66`,display:"flex",alignItems:"center",gap:12,animation:"toastIn 0.35s cubic-bezier(0.34,1.56,0.64,1) forwards",maxWidth:300}}>
          <div style={{fontSize:32}}>{newBadge.icon}</div>
          <div><div style={{fontSize:11,color:T.goldLight,fontWeight:700,letterSpacing:1,textTransform:"uppercase",marginBottom:2}}>Badge Unlocked</div><div style={{fontSize:14,fontWeight:800}}>{newBadge.name}</div><div style={{fontSize:11,color:"#9ab09e",marginTop:1}}>{newBadge.desc}</div></div>
        </div>
      )}

      {/* Weekly wizard */}
      {showWizard&&<WeeklyWizard onClose={()=>setShowWizard(false)} onSaved={()=>{setShowWizard(false);loadDashboard();}} initialData={d}/>}

      {/* Header */}
      <div style={{background:T.bgDark,padding:"14px 28px",display:"flex",justifyContent:"space-between",alignItems:"center",boxShadow:`0 4px 20px ${T.shadowMd}`}}>
        <div style={{display:"flex",alignItems:"center",gap:14}}>
          <div style={{width:48,height:48,borderRadius:12,flexShrink:0,background:"#e8eef4",boxShadow:`0 4px 14px rgba(0,0,0,0.4)`,border:`1.5px solid #3d5240`,display:"flex",alignItems:"center",justifyContent:"center"}}>
            <svg width="38" height="38" viewBox="0 0 100 100" fill="none">
              <path d="M 18 72 A 42 42 0 1 1 82 72" stroke="#4a7fa5" strokeWidth="7" strokeLinecap="round" fill="none"/>
              <path d="M 28 75 A 30 30 0 1 1 72 75" stroke="#2d5f80" strokeWidth="4.5" strokeLinecap="round" fill="none"/>
              <rect x="32" y="58" width="7" height="16" rx="2" fill="#2d5f80"/>
              <rect x="42" y="50" width="7" height="24" rx="2" fill="#3a7aa8"/>
              <rect x="52" y="41" width="7" height="33" rx="2" fill="#4a8fbf"/>
              <rect x="62" y="33" width="7" height="41" rx="2" fill="#5aa3d4"/>
              <circle cx="65.5" cy="30" r="4" fill="#7ec8e3"/>
            </svg>
          </div>
          <div>
            <div style={{fontSize:17,fontWeight:900,color:T.white,letterSpacing:-0.2,fontFamily:"'Playfair Display',serif",lineHeight:1.1}}>JD Analytics & Solutions</div>
            <div style={{fontSize:10,color:"#6a8a6e",marginTop:2,letterSpacing:0.3}}>Digital Clone · Business Intelligence</div>
          </div>
        </div>

        {/* Mode tabs */}
        <div style={{display:"flex",gap:4,background:"#111a12",borderRadius:14,padding:4,boxShadow:`inset 0 2px 8px rgba(0,0,0,0.35)`}}>
          {[
            {id:"snapshot",icon:"📊",label:"Real Time Status"},
            {id:"whatif",  icon:"🎮",label:"Predictive Playground"},
          ].map(({id,icon,label})=>(
            <button key={id} onClick={()=>setMode(id)} style={{padding:"9px 18px",borderRadius:10,fontSize:12,fontWeight:700,cursor:"pointer",border:"none",fontFamily:"inherit",letterSpacing:0.2,background:mode===id?T.green:"transparent",color:mode===id?T.white:"#4a6a4e",boxShadow:mode===id?`0 3px 10px rgba(0,0,0,0.3)`:"none",transition:"all 0.2s",display:"flex",alignItems:"center",gap:7}}>
              <span>{icon}</span><span>{label}</span>
            </button>
          ))}
        </div>

        {/* Right: update button + live indicator */}
        <div style={{display:"flex",alignItems:"center",gap:12}}>
          <button onClick={()=>setShowWizard(true)}
            style={{padding:"9px 18px",borderRadius:10,background:T.gold,border:"none",color:T.white,fontSize:12,fontWeight:800,cursor:"pointer",fontFamily:"inherit",boxShadow:`0 4px 12px ${T.gold}44`,display:"flex",alignItems:"center",gap:7,transition:"all 0.2s"}}
            onMouseEnter={e=>e.currentTarget.style.transform="translateY(-1px)"}
            onMouseLeave={e=>e.currentTarget.style.transform=""}>
            ✏️ Update Numbers
          </button>
          <div style={{display:"flex",flexDirection:"column",alignItems:"flex-end",gap:3}}>
            <div style={{display:"flex",alignItems:"center",gap:7}}>
              <div style={{width:8,height:8,borderRadius:"50%",background:loading?T.gold:error?T.red:T.greenGlow,boxShadow:`0 0 ${pulse?8:4}px ${loading?T.gold:error?T.red:T.greenGlow}`,transition:"box-shadow 1.5s"}}/>
              <span style={{fontSize:11,color:"#4a6a4e",fontWeight:600}}>{loading?"Loading...":error?"Error":USE_MOCK?"Mock data":"Live data"}</span>
            </div>
            {lastUpdated&&<span style={{fontSize:9,color:"#3a5a3e"}}>Updated {lastUpdated.toLocaleTimeString()}</span>}
          </div>
        </div>
      </div>

      {/* Error state */}
      {error&&!loading&&(
        <div style={{margin:"16px 28px",background:T.redPale,border:`2px solid ${T.red}44`,borderRadius:12,padding:"12px 18px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <span style={{fontSize:13,color:T.red,fontWeight:700}}>⚠️ Could not load data: {error}</span>
          <button onClick={loadDashboard} style={{background:T.red,color:"#fff",border:"none",borderRadius:8,padding:"6px 14px",cursor:"pointer",fontFamily:"inherit",fontWeight:700,fontSize:12}}>Retry</button>
        </div>
      )}

      {/* Loading state */}
      {loading&&(
        <div style={{display:"flex",alignItems:"center",justifyContent:"center",padding:60,gap:16}}>
          <Spinner/><span style={{fontSize:14,color:T.textMid,fontWeight:600}}>Loading your dashboard...</span>
        </div>
      )}

      {/* REAL TIME STATUS */}
      {!loading&&mode==="snapshot"&&(
        <div style={{padding:"22px 28px",maxWidth:1280,margin:"0 auto",animation:"fadeIn 0.4s ease"}}>
          <StatusBanner banner={d.status_banner}/>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14,margin:"16px 0"}}>
            <div style={{background:T.bgCard,border:`1.5px solid ${T.border}`,borderRadius:18,padding:"18px 22px",boxShadow:`0 2px 12px ${T.shadow}`}}>
              <div style={{fontSize:12,fontWeight:800,color:T.textMid,textTransform:"uppercase",letterSpacing:0.8,marginBottom:12}}>Your Business Score</div>
              <XPStrip xp={d.score?.xp||0}/>
            </div>
            <div style={{background:T.bgCard,border:`1.5px solid ${T.border}`,borderRadius:18,padding:"18px 22px",boxShadow:`0 2px 12px ${T.shadow}`}}>
              <div style={{fontSize:12,fontWeight:800,color:T.textMid,textTransform:"uppercase",letterSpacing:0.8,marginBottom:12}}>Achievements</div>
              <BadgeShelf badges={d.badges}/>
            </div>
          </div>

          <div style={{display:"grid",gridTemplateColumns:"repeat(2,1fr)",gap:14,marginBottom:14}}>
            {/* Cash */}
            <MetricCard icon="💵" title="Your Money" status={cashStatus(d)}>
              <div style={{display:"flex",gap:16,alignItems:"flex-end",marginBottom:14}}>
                <div>
                  <div style={{fontSize:11,color:T.textLight,marginBottom:3}}>Cash in the bank right now</div>
                  <div style={{fontSize:34,fontWeight:900,color:statusColor(cashStatus(d)),letterSpacing:-1,fontFamily:"'Playfair Display',serif"}}>${(d.cash.amount||0).toLocaleString()}</div>
                </div>
              </div>
              <div style={{marginBottom:12}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                  <span style={{fontSize:11,color:T.textSoft,fontWeight:700}}>How long it lasts</span>
                  <span style={{fontSize:11,color:T.textLight}}>~{(d.cash.weeks_left||0).toFixed(1)} weeks</span>
                </div>
                <HealthBar val={Math.round((d.cash.weeks_left||0)*10)} max={80}/>
              </div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
                <div style={{background:T.redPale,borderRadius:12,padding:"10px 14px",border:`1px solid ${T.red}33`}}>
                  <div style={{fontSize:10,color:T.textLight,marginBottom:3}}>Going out / week</div>
                  <div style={{fontSize:20,fontWeight:900,color:T.red,fontFamily:"'Playfair Display',serif"}}>${(d.cash.weekly_out||0).toLocaleString()}</div>
                </div>
                <div style={{background:(d.cash.weekly_in||0)<500?T.redPale:T.greenPale,borderRadius:12,padding:"10px 14px",border:`1px solid ${(d.cash.weekly_in||0)<500?T.red:T.green}33`}}>
                  <div style={{fontSize:10,color:T.textLight,marginBottom:3}}>Coming in / week</div>
                  <div style={{fontSize:20,fontWeight:900,color:(d.cash.weekly_in||0)<500?T.red:T.green,fontFamily:"'Playfair Display',serif"}}>${(d.cash.weekly_in||0).toLocaleString()}</div>
                </div>
              </div>
            </MetricCard>

            {/* Workload */}
            <MetricCard icon="📋" title="How Slammed Are You?" status={workStatus(d)}>
              <div style={{marginBottom:14}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
                  <span style={{fontSize:11,color:T.textSoft,fontWeight:700}}>Breathing room</span>
                  <span style={{fontSize:11,color:T.textLight}}>100 = totally free</span>
                </div>
                <HealthBar val={100-(d.workload.stress_score||0)} max={100} size="lg"/>
              </div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
                <MiniStat label="Hours backed up"      val={`${d.workload.backlog_hrs||0} hrs`}    status={(d.workload.backlog_hrs||0)>20?"bad":undefined}/>
                <MiniStat label="Customer wait"        val={`${d.workload.wait_days||0} days`}     status={(d.workload.wait_days||0)>7?"bad":undefined}/>
                <MiniStat label="Capacity / week"      val={`${d.workload.sustainable_cap||0} hrs`}/>
                <MiniStat label="Helpers"              val={d.labor.num_subs===0?"None":d.labor.num_subs} status={d.labor.num_subs===0&&(d.workload.stress_score||0)>70?"bad":undefined}/>
              </div>
            </MetricCard>

            {/* Pipeline */}
            <MetricCard icon="🔧" title="Jobs Coming In" status={pipeStatus(d)}>
              <div style={{marginBottom:14}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
                  <span style={{fontSize:11,color:T.textSoft,fontWeight:700}}>How often you land the job</span>
                  <span style={{fontSize:11,color:T.textLight}}>{Math.round((d.pipeline.win_rate||0)*10)} out of every 10 quotes</span>
                </div>
                <HealthBar val={Math.round((d.pipeline.win_rate||0)*100)} max={100}/>
              </div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:8,marginBottom:12}}>
                <MiniStat label="Interested / wk"  val={d.pipeline.leads_per_week||0}/>
                <MiniStat label="Jobs won / wk"    val={(d.pipeline.closes_12w/12||0).toFixed(2)}/>
                <MiniStat label="Avg job size"      val={`$${(d.pipeline.avg_project_value||0).toLocaleString()}`}/>
              </div>
              <div style={{background:T.greenPale,borderRadius:12,padding:"10px 14px",border:`1px solid ${T.green}44`,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                <span style={{fontSize:12,color:T.textMid,fontWeight:600}}>Expected next 3 months</span>
                <span style={{fontSize:22,fontWeight:900,color:T.green,fontFamily:"'Playfair Display',serif"}}>${(d.pipeline.revenue_12w||0).toLocaleString()}</span>
              </div>
            </MetricCard>

            {/* Quality */}
            <MetricCard icon="😊" title="Are Customers Happy?" status={qualStatus(d)}>
              <div style={{marginBottom:14}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
                  <span style={{fontSize:11,color:T.textSoft,fontWeight:700}}>Happiness level</span>
                  <span style={{fontSize:11,color:T.textLight}}>{(d.quality.score||0)<60?"Delays frustrating people":(d.quality.score||0)<80?"Room to improve":"They love the work"}</span>
                </div>
                <HealthBar val={d.quality.score||0} max={100} size="lg"/>
              </div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
                <div><div style={{fontSize:10,color:T.textLight,marginBottom:5,fontWeight:600}}>Chance they come back</div><HealthBar val={Math.round((d.quality.retention_likelihood||0)*100)} max={100} size="sm"/></div>
                <div><div style={{fontSize:10,color:T.textLight,marginBottom:5,fontWeight:600}}>Chance they tell friends</div><HealthBar val={Math.round((d.quality.referral_likelihood||0)*100)} max={100} size="sm"/></div>
              </div>
            </MetricCard>
          </div>

          {/* Bottom strip */}
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:14}}>
            <div style={{background:T.bgCard,border:`1.5px solid ${T.border}`,borderRadius:18,padding:"16px 20px",boxShadow:`0 2px 12px ${T.shadow}`}}>
              <div style={{fontSize:12,fontWeight:800,color:T.textMid,textTransform:"uppercase",letterSpacing:0.8,marginBottom:10}}>📅 Steady Monthly Income</div>
              <div style={{fontSize:28,fontWeight:900,color:(d.recurring.mrr||0)===0?T.red:T.green,fontFamily:"'Playfair Display',serif"}}>${(d.recurring.mrr||0).toLocaleString()}</div>
              <div style={{fontSize:11,color:T.textLight,marginTop:6,lineHeight:1.5}}>{(d.recurring.retainer_clients||0)===0?"No regular clients yet. Every dollar depends on landing new jobs.":`${d.recurring.retainer_clients} regular client${d.recurring.retainer_clients!==1?"s":""} · $${(d.recurring.mrr_month12||0).toLocaleString()} by month 12`}</div>
            </div>
            <div style={{background:T.bgCard,border:`1.5px solid ${T.border}`,borderRadius:18,padding:"16px 20px",boxShadow:`0 2px 12px ${T.shadow}`}}>
              <div style={{fontSize:12,fontWeight:800,color:T.textMid,textTransform:"uppercase",letterSpacing:0.8,marginBottom:10}}>👷 Team & Owner</div>
              <div style={{fontSize:28,fontWeight:900,color:T.textDark,fontFamily:"'Playfair Display',serif"}}>{(d.labor.num_subs||0)===0?"Solo":`You + ${d.labor.num_subs}`}</div>
              <div style={{fontSize:11,color:T.textLight,marginTop:6,lineHeight:1.5}}>{(d.labor.num_subs||0)===0?"Just you right now. No helpers hired yet.":`${d.labor.num_subs} helper${d.labor.num_subs!==1?"s":""} active · ${Math.round((d.labor.gross_margin||0)*100)}% margin`}</div>
            </div>
            <div onClick={()=>setShowWizard(true)}
              style={{background:T.bgDark,borderRadius:18,padding:"16px 20px",cursor:"pointer",display:"flex",flexDirection:"column",justifyContent:"center",alignItems:"center",gap:10,border:`1.5px solid ${T.borderDark}`,boxShadow:`0 4px 20px ${T.shadowMd}`,transition:"transform 0.15s ease"}}
              onMouseEnter={e=>e.currentTarget.style.transform="translateY(-3px)"}
              onMouseLeave={e=>e.currentTarget.style.transform=""}>
              <span style={{fontSize:30}}>✏️</span>
              <div style={{fontSize:15,fontWeight:900,color:T.white,fontFamily:"'Playfair Display',serif"}}>Update My Numbers</div>
              <div style={{fontSize:11,color:"#4a6a4e",textAlign:"center",lineHeight:1.5}}>5-step check-in · takes 2 minutes</div>
            </div>
          </div>
        </div>
      )}

      {/* PREDICTIVE PLAYGROUND */}
      {!loading&&mode==="whatif"&&<PredictionPanel liveData={d}/>}
    </div>
  );
}
