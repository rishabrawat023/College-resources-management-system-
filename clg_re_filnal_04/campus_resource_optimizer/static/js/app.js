const $ = (id) => document.getElementById(id);
const api = async (url, options={}) => {
  const response = await fetch(url, {headers:{"Content-Type":"application/json"}, ...options});
  const data = await response.json().catch(()=>({success:false,error:"Invalid server response"}));
  if (!response.ok || data.success === false) throw new Error(data.error || "Request failed");
  return data;
};
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function toast(message, error=false){const el=$("toast");el.textContent=message;el.className="toast show"+(error?" error":"");setTimeout(()=>el.className="toast",3000);}
function showModal(id){$(id).classList.add("show");}
function closeModal(id){$(id).classList.remove("show");}
function go(view){document.querySelectorAll(".view").forEach(v=>v.classList.remove("active"));$(view+"View").classList.add("active");document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.view===view));$("pageTitle").textContent=({overview:"Overview",resources:"Resources",bookings:"Bookings",waiting:"Waiting list"})[view];if(view==="overview")loadDashboard();if(view==="resources")loadResources();if(view==="bookings")loadBookings();if(view==="waiting")loadWaiting();}
document.querySelectorAll(".nav-item").forEach(b=>b.addEventListener("click",()=>go(b.dataset.view)));
document.querySelectorAll("[data-go]").forEach(b=>b.addEventListener("click",()=>go(b.dataset.go)));
document.querySelectorAll("[data-close]").forEach(b=>b.addEventListener("click",()=>closeModal(b.dataset.close)));
document.querySelectorAll(".modal-backdrop").forEach(m=>m.addEventListener("click",e=>{if(e.target===m)closeModal(m.id)}));
$("todayLabel").textContent=new Intl.DateTimeFormat("en-IN",{weekday:"short",day:"numeric",month:"short",year:"numeric"}).format(new Date());

async function loadDashboard(){
 try{
  const d=await api("/api/dashboard");$("statResources").textContent=d.total_resources;$("statBookings").textContent=d.total_bookings;$("statWaiting").textContent=d.waiting_count;$("statAvailable").textContent=d.available_count;
  const icons={"Classroom":"▤","Computer Lab":"⌘","Seminar Hall":"▣","Auditorium":"▥"};
  $("distribution").innerHTML=Object.entries(d.type_counts).map(([k,v])=>`<div class="distribution-card"><div class="dist-icon">${icons[k]}</div><b>${k}</b><strong>${v}</strong><small>registered spaces</small></div>`).join("");
  $("recentRows").innerHTML=d.recent_bookings.length?d.recent_bookings.map(b=>`<tr><td><b>${escapeHtml(b.resource_name)}</b></td><td>${escapeHtml(b.booked_by)}</td><td>${escapeHtml(b.date)}</td><td>${escapeHtml(b.start_time)}–${escapeHtml(b.end_time)}</td><td>${escapeHtml(b.purpose)}</td></tr>`).join(""):`<tr><td colspan="5" class="empty">No bookings yet. Create your first booking.</td></tr>`;
 }catch(e){toast(e.message,true)}
}
async function loadResources(){
 try{
  const params=new URLSearchParams({q:$("resourceSearch").value,type:$("typeFilter").value,sort:$("sortFilter").value});
  const d=await api("/api/resources?"+params);
  $("resourceGrid").innerHTML=d.resources.length?d.resources.map(r=>`<article class="resource-card"><div class="resource-card-head"><span class="resource-type">${escapeHtml(r.type)}</span><span class="soft-pill">${escapeHtml(r.id)}</span></div><h4>${escapeHtml(r.name)}</h4><div class="resource-location">⌖ ${escapeHtml(r.location)}</div><div class="resource-capacity"><strong>${r.capacity}</strong><span>person capacity</span></div><div class="feature-list">${r.smartboard?'<span class="feature">Smartboard</span>':''}${r.projector?'<span class="feature">Projector</span>':''}${r.pcs?`<span class="feature">${r.pcs} PCs</span>`:''}${r.ac?'<span class="feature">AC</span>':'<span class="feature">No AC</span>'}</div><div class="card-actions"><button class="small-btn" onclick="editResource('${r.id}')">Edit</button><button class="small-btn danger" onclick="deleteResource('${r.id}')">Delete</button></div></article>`).join(""):'<div class="panel empty">No resources match your search.</div>';
 }catch(e){toast(e.message,true)}
}
["resourceSearch","typeFilter","sortFilter"].forEach(id=>$(id).addEventListener(id==="resourceSearch"?"input":"change",loadResources));
$("addResourceBtn").onclick=()=>{ $("resourceForm").reset();$("resourceId").value="";$("resourceModalTitle").textContent="Add resource";showModal("resourceModal");};
async function editResource(id){
 try{const d=await api("/api/resources");const r=d.resources.find(x=>x.id===id);if(!r)return;
 $("resourceId").value=r.id;$("rName").value=r.name;$("rType").value=r.type;$("rCapacity").value=r.capacity;$("rLocation").value=r.location;$("rPcs").value=r.pcs;$("rSmartboard").checked=r.smartboard;$("rProjector").checked=r.projector;$("rAc").checked=r.ac;$("resourceModalTitle").textContent="Edit resource";showModal("resourceModal");
 }catch(e){toast(e.message,true)}
}
async function deleteResource(id){if(!confirm("Delete this resource? This cannot be undone."))return;try{await api("/api/resources/"+id,{method:"DELETE"});toast("Resource deleted.");loadResources();loadDashboard();}catch(e){toast(e.message,true)}}
$("resourceForm").onsubmit=async e=>{e.preventDefault();const id=$("resourceId").value;const payload={name:$("rName").value,type:$("rType").value,capacity:$("rCapacity").value,location:$("rLocation").value,pcs:$("rPcs").value,smartboard:$("rSmartboard").checked,projector:$("rProjector").checked,ac:$("rAc").checked};try{await api(id?"/api/resources/"+id:"/api/resources",{method:id?"PUT":"POST",body:JSON.stringify(payload)});closeModal("resourceModal");toast(id?"Resource updated.":"Resource added.");loadResources();loadDashboard();}catch(e){toast(e.message,true)}};

async function populateResourceSelect(){const d=await api("/api/resources");$("bResource").innerHTML=d.resources.map(r=>`<option value="${escapeHtml(r.id)}">${escapeHtml(r.name)} · ${escapeHtml(r.type)}</option>`).join("");}
$("newBookingBtn").onclick=async()=>{try{await populateResourceSelect();$("bookingForm").reset();const today=new Date();$("bDate").min=today.toISOString().slice(0,10);$("bDate").value=today.toISOString().slice(0,10);showModal("bookingModal");}catch(e){toast(e.message,true)}};
async function loadBookings(){try{const d=await api("/api/bookings");$("bookingCount").textContent=d.bookings.length+" bookings";$("bookingRows").innerHTML=d.bookings.length?d.bookings.map(b=>`<tr><td><b>${escapeHtml(b.resource_name)}</b></td><td>${escapeHtml(b.booked_by)}</td><td>${escapeHtml(b.date)}</td><td>${escapeHtml(b.start_time)}–${escapeHtml(b.end_time)}</td><td>${escapeHtml(b.purpose)}</td><td><button class="small-btn danger" onclick="cancelBooking('${b.id}')">Cancel</button></td></tr>`).join(""):'<tr><td colspan="6" class="empty">No confirmed bookings.</td></tr>';}catch(e){toast(e.message,true)}}
$("bookingForm").onsubmit=async e=>{e.preventDefault();const payload={resource_id:$("bResource").value,booked_by:$("bName").value,purpose:$("bPurpose").value,date:$("bDate").value,start_time:$("bStart").value,end_time:$("bEnd").value};try{const d=await api("/api/bookings",{method:"POST",body:JSON.stringify(payload)});closeModal("bookingModal");toast(d.message||(d.status==="waiting"?"Added to waiting list.":"Booking confirmed."));loadBookings();loadWaiting();loadDashboard();}catch(e){toast(e.message,true)}};
async function cancelBooking(id){if(!confirm("Cancel this booking?"))return;try{const d=await api("/api/bookings/"+id,{method:"DELETE"});toast(d.message);loadBookings();loadWaiting();loadDashboard();}catch(e){toast(e.message,true)}}
async function loadWaiting(){try{const d=await api("/api/waiting-list");$("waitingCount").textContent=d.waiting_list.length+" requests";$("waitingRows").innerHTML=d.waiting_list.length?d.waiting_list.map((w,i)=>`<tr><td><span class="soft-pill">#${i+1}</span></td><td><b>${escapeHtml(w.resource_name)}</b></td><td>${escapeHtml(w.booked_by)}</td><td>${escapeHtml(w.date)}</td><td>${escapeHtml(w.start_time)}–${escapeHtml(w.end_time)}</td><td>${escapeHtml(w.purpose)}</td><td><button class="small-btn danger" onclick="cancelWaiting('${w.id}')">Remove</button></td></tr>`).join(""):'<tr><td colspan="7" class="empty">The waiting list is empty.</td></tr>';}catch(e){toast(e.message,true)}}
async function cancelWaiting(id){if(!confirm("Remove this request from the waiting list?"))return;try{await api("/api/waiting-list/"+id,{method:"DELETE"});toast("Waiting request removed.");loadWaiting();loadDashboard();}catch(e){toast(e.message,true)}}
loadDashboard();
