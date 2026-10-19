// The bookings dashboard, built with React.
//
// No build step and no Node.js: React and htm load straight from a CDN.
// htm lets us write HTML-like templates (html`<div>...</div>`) instead of JSX,
// so the browser can run this file as it is.
import React, { useEffect, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";

const html = htm.bind(React.createElement);
const REFRESH_SECONDS = 30; // ask the server for new bookings every 30 seconds

// ---------- small helpers ----------

// Simple line icons (paths from the Lucide icon set).
const ICONS = {
  calendar: "M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z",
  clock: "M12 6v6l4 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
  chart: "M3 3v18h18M7 15l4-4 3 3 5-6",
  gauge: "M12 14l4-4M3.34 19a10 10 0 1 1 17.32 0",
  phone: "M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z",
  chat: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3",
};

function Icon({ name, size = 20 }) {
  return html`
    <svg viewBox="0 0 24 24" width=${size} height=${size} fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d=${ICONS[name]} />
    </svg>`;
}

// Phone numbers are saved as 8 digits ("91234567"); links need the country code.
const callLink = (phone) => `tel:+968${phone}`;
const whatsappLink = (phone) => `https://wa.me/968${phone}`;

// ---------- the pieces of the page ----------

function StatCard({ icon, label, value, hint, progress }) {
  return html`
    <div className="card stat">
      <div className="stat-icon"><${Icon} name=${icon} /></div>
      <div className="stat-label">${label}</div>
      <div className="stat-value">${value}</div>
      ${progress !== undefined && html`
        <div className="bar"><div className="bar-fill" style=${{ width: `${progress}%` }}></div></div>`}
      <div className="stat-hint">${hint}</div>
    </div>`;
}

function ContactButtons({ phone }) {
  return html`
    <span className="contact">
      <a className="icon-btn" href=${callLink(phone)} title="اتصال"><${Icon} name="phone" size=${16} /></a>
      <a className="icon-btn" href=${whatsappLink(phone)} target="_blank" rel="noopener" title="واتساب">
        <${Icon} name="chat" size=${16} />
      </a>
    </span>`;
}

// The 7 day buttons on top of the day view, each with a small "how full" bar.
function DayTabs({ days, hours, countByDay, selected, onSelect }) {
  return html`
    <div className="day-tabs" role="tablist">
      ${days.map((day, i) => {
        const count = countByDay[day.date] || 0;
        return html`
          <button key=${day.date} role="tab" aria-selected=${day.date === selected}
                  className=${"day-tab" + (day.date === selected ? " active" : "")}
                  onClick=${() => onSelect(day.date)}>
            <span className="day-name">${i === 0 ? "اليوم" : day.name}</span>
            <span className="day-date">${day.short}</span>
            <span className="mini-bar"><span style=${{ width: `${(100 * count) / hours.length}%` }}></span></span>
            <span className="day-count">${count} حجز</span>
          </button>`;
      })}
    </div>`;
}

// Every hour of the selected day: booked (with the customer), free, or already over.
function DaySlots({ day, hours, byKey, isToday, nowHour }) {
  return html`
    <div className="slots">
      ${hours.map(({ hour, label }) => {
        const booking = byKey.get(`${day.date}|${hour}`);
        const past = isToday && hour < nowHour;
        const live = isToday && hour === nowHour;
        const state = booking ? "booked" : past ? "past" : "free";
        return html`
          <div key=${hour} className=${`slot ${state}${live ? " live" : ""}`}>
            <div className="slot-time">${label}</div>
            ${booking
              ? html`
                  <div className="slot-body">
                    <div className="slot-name">${booking.name}</div>
                    <div className="slot-phone" dir="ltr">${booking.phone}</div>
                  </div>
                  <${ContactButtons} phone=${booking.phone} />`
              : html`<div className="slot-body muted">${past ? "انتهى الوقت" : "متاح للحجز"}</div>`}
            ${live && html`<span className="live-badge">جاري الحين</span>`}
          </div>`;
      })}
    </div>`;
}

// The whole week at a glance: days across, hours down. Click a day to open it.
function WeekGrid({ days, hours, byKey, selected, onSelect, nowHour }) {
  return html`
    <div className="scroll">
      <table className="week">
        <thead>
          <tr>
            <th className="corner"></th>
            ${days.map((day, i) => html`
              <th key=${day.date} className=${day.date === selected ? "selected" : ""}>
                <button className="link-btn" onClick=${() => onSelect(day.date)}>
                  ${i === 0 ? "اليوم" : day.name}<br /><span className="muted">${day.short}</span>
                </button>
              </th>`)}
          </tr>
        </thead>
        <tbody>
          ${hours.map(({ hour, label }) => html`
            <tr key=${hour}>
              <th className="hour">${label}</th>
              ${days.map((day, i) => {
                const booking = byKey.get(`${day.date}|${hour}`);
                const past = i === 0 && hour < nowHour;
                return html`
                  <td key=${day.date}>
                    <div className=${"cell " + (booking ? "booked" : past ? "past" : "free")}
                         title=${booking ? `${booking.name} · ${booking.phone}` : ""}>
                      ${booking ? booking.name : ""}
                    </div>
                  </td>`;
              })}
            </tr>`)}
        </tbody>
      </table>
    </div>`;
}

// Every booking of the week, with a search box (by name or number).
function BookingList({ bookings, dayByDate, labelByHour }) {
  const [search, setSearch] = useState("");
  const query = search.trim();
  const shown = bookings.filter((b) => b.name.includes(query) || b.phone.includes(query));

  return html`
    <div>
      <label className="search">
        <${Icon} name="search" size=${18} />
        <input type="search" placeholder="ابحث بالاسم أو الرقم" value=${search}
               onChange=${(e) => setSearch(e.target.value)} />
      </label>
      ${shown.length === 0
        ? html`<div className="empty">ما فيه حجوزات</div>`
        : html`
            <ul className="booking-list">
              ${shown.map((b) => html`
                <li key=${b.id}>
                  <div className="date-chip">
                    <span>${dayByDate[b.date].name}</span>
                    <small>${dayByDate[b.date].short}</small>
                  </div>
                  <div className="booking-info">
                    <div className="booking-name">${b.name}</div>
                    <div className="muted">${labelByHour[b.hour]} · <span dir="ltr">${b.phone}</span></div>
                  </div>
                  <${ContactButtons} phone=${b.phone} />
                </li>`)}
            </ul>`}
    </div>`;
}

// ---------- the whole page ----------

function App() {
  const [data, setData] = useState(null);       // what /api/dashboard returned
  const [failed, setFailed] = useState(false);  // true if the last refresh didn't work
  const [selected, setSelected] = useState(null); // the date open in the day view

  // Fetch the bookings now, then again every REFRESH_SECONDS.
  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("/api/dashboard");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        setData(await response.json());
        setFailed(false);
      } catch {
        setFailed(true); // keep showing the last data we had
      }
    }
    load();
    const timer = setInterval(load, REFRESH_SECONDS * 1000);
    return () => clearInterval(timer); // stop the timer if the page goes away
  }, []);

  if (!data) {
    return html`<div className="loading">${failed ? "تعذّر تحميل البيانات، حدّث الصفحة" : "جاري التحميل…"}</div>`;
  }

  // Ready-made lookups, so the pieces below stay simple.
  const { days, hours, bookings, now_hour: nowHour } = data;
  const today = days[0].date;
  const day = days.find((d) => d.date === selected) || days[0];
  const byKey = new Map(bookings.map((b) => [`${b.date}|${b.hour}`, b]));
  const dayByDate = Object.fromEntries(days.map((d) => [d.date, d]));
  const labelByHour = Object.fromEntries(hours.map((h) => [h.hour, h.label]));
  const countByDay = {};
  bookings.forEach((b) => { countByDay[b.date] = (countByDay[b.date] || 0) + 1; });

  // The numbers on top.
  const todayCount = countByDay[today] || 0;
  const freeToday = hours.filter((h) => h.hour > nowHour && !byKey.has(`${today}|${h.hour}`)).length;
  const occupancy = Math.round((100 * bookings.length) / (days.length * hours.length));
  const next = bookings.find((b) => b.date > today || b.hour > nowHour);

  return html`
    <main>
      <header className="top">
        <div className="brand">
          <div className="logo">⚽</div>
          <div>
            <h1>لوحة حجوزات ملعب الترتان</h1>
            <div className="muted">الدوام يوميًا من ${hours[0].label} إلى 12 الليل</div>
          </div>
        </div>
        <div className=${"live-pill" + (failed ? " offline" : "")}>
          <span className="dot"></span>
          ${failed ? "غير متصل" : "مباشر"} · آخر تحديث ${data.updated}
        </div>
      </header>

      ${next && html`
        <div className="next-up">
          <${Icon} name="clock" size=${18} />
          الحجز القادم: <b>${next.date === today ? "اليوم" : dayByDate[next.date].name}</b>
          الساعة <b>${labelByHour[next.hour]}</b> باسم <b>${next.name}</b>
        </div>`}

      <section className="stats">
        <${StatCard} icon="calendar" label="حجوزات اليوم" value=${todayCount} hint=${`من ${hours.length} ساعات`} />
        <${StatCard} icon="clock" label="الساعات المتاحة اليوم" value=${freeToday} hint="باقي من اليوم" />
        <${StatCard} icon="chart" label="حجوزات الأسبوع" value=${bookings.length} hint="الأيام السبعة الجاية" />
        <${StatCard} icon="gauge" label="نسبة الإشغال" value=${`${occupancy}%`} hint="من كل ساعات الأسبوع"
                     progress=${occupancy} />
      </section>

      <div className="columns">
        <section className="card">
          <h2>جدول اليوم</h2>
          <${DayTabs} days=${days} hours=${hours} countByDay=${countByDay}
                      selected=${day.date} onSelect=${setSelected} />
          <${DaySlots} day=${day} hours=${hours} byKey=${byKey}
                       isToday=${day.date === today} nowHour=${nowHour} />
        </section>

        <section className="card">
          <h2>الحجوزات القادمة <span className="count">${bookings.length}</span></h2>
          <${BookingList} bookings=${bookings} dayByDate=${dayByDate} labelByHour=${labelByHour} />
        </section>
      </div>

      <section className="card">
        <h2>نظرة على الأسبوع</h2>
        <${WeekGrid} days=${days} hours=${hours} byKey=${byKey}
                     selected=${day.date} onSelect=${setSelected} nowHour=${nowHour} />
      </section>
    </main>`;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);
