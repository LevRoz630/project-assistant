import { useState, useEffect } from 'react'
import './Calendar.css'

const API_BASE = 'http://localhost:8000'

function Calendar() {
  const [view, setView] = useState('today') // 'today' or 'week'
  const [events, setEvents] = useState([])
  const [eventsByDate, setEventsByDate] = useState({})
  const [loading, setLoading] = useState(true)
  const [showNewEvent, setShowNewEvent] = useState(false)
  const [newEvent, setNewEvent] = useState({
    subject: '',
    date: new Date().toISOString().split('T')[0],
    startTime: '09:00',
    endTime: '10:00',
    location: '',
  })

  useEffect(() => {
    if (view === 'today') {
      loadTodayEvents()
    } else {
      loadWeekEvents()
    }
  }, [view])

  const loadTodayEvents = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/calendar/today`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setEvents(data.events || [])
        setEventsByDate({})
      }
    } catch (error) {
      console.error('Failed to load events:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadWeekEvents = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/calendar/week`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setEventsByDate(data.events_by_date || {})
        setEvents([])
      }
    } catch (error) {
      console.error('Failed to load events:', error)
    } finally {
      setLoading(false)
    }
  }

  const createEvent = async () => {
    if (!newEvent.subject.trim()) return

    const start = `${newEvent.date}T${newEvent.startTime}:00`
    const end = `${newEvent.date}T${newEvent.endTime}:00`

    try {
      const res = await fetch(`${API_BASE}/calendar/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          subject: newEvent.subject,
          start,
          end,
          location: newEvent.location || null,
        }),
      })

      if (res.ok) {
        setShowNewEvent(false)
        setNewEvent({
          subject: '',
          date: new Date().toISOString().split('T')[0],
          startTime: '09:00',
          endTime: '10:00',
          location: '',
        })
        view === 'today' ? loadTodayEvents() : loadWeekEvents()
      }
    } catch (error) {
      console.error('Failed to create event:', error)
    }
  }

  const deleteEvent = async (eventId) => {
    if (!confirm('Delete this event?')) return

    try {
      const res = await fetch(`${API_BASE}/calendar/delete/${eventId}`, {
        method: 'DELETE',
        credentials: 'include',
      })

      if (res.ok) {
        view === 'today' ? loadTodayEvents() : loadWeekEvents()
      }
    } catch (error) {
      console.error('Failed to delete event:', error)
    }
  }

  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    })
  }

  const renderEvent = (event) => (
    <div key={event.id} className={`event-item ${event.is_all_day ? 'all-day' : ''}`}>
      <div className="event-time">
        {event.is_all_day ? 'All day' : `${event.start_time} - ${event.end_time}`}
      </div>
      <div className="event-details">
        <div className="event-subject">{event.subject}</div>
        {event.location && (
          <div className="event-location">
            <LocationIcon />
            {event.location}
          </div>
        )}
        {event.organizer && (
          <div className="event-organizer">Organized by {event.organizer}</div>
        )}
      </div>
      <button className="event-delete" onClick={() => deleteEvent(event.id)}>
        <TrashIcon />
      </button>
    </div>
  )

  return (
    <>
      <div className="content-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Calendar</h2>
          <div style={{ display: 'flex', gap: '12px' }}>
            <div className="view-toggle">
              <button
                className={`view-btn ${view === 'today' ? 'active' : ''}`}
                onClick={() => setView('today')}
              >
                Today
              </button>
              <button
                className={`view-btn ${view === 'week' ? 'active' : ''}`}
                onClick={() => setView('week')}
              >
                Week
              </button>
            </div>
            <button className="btn btn-primary" onClick={() => setShowNewEvent(true)}>
              New Event
            </button>
          </div>
        </div>
      </div>

      <div className="content-body">
        {loading ? (
          <div className="loading">
            <div className="loading-spinner"></div>
          </div>
        ) : view === 'today' ? (
          <div className="events-today">
            <h3 className="date-header">{formatDate(new Date())}</h3>
            {events.length === 0 ? (
              <div className="empty-state">
                <h3>No events today</h3>
                <p>Your schedule is clear</p>
              </div>
            ) : (
              <div className="events-list">
                {events.map(renderEvent)}
              </div>
            )}
          </div>
        ) : (
          <div className="events-week">
            {Object.keys(eventsByDate).length === 0 ? (
              <div className="empty-state">
                <h3>No events this week</h3>
                <p>Your schedule is clear for the next 7 days</p>
              </div>
            ) : (
              Object.entries(eventsByDate).map(([date, dateEvents]) => (
                <div key={date} className="day-section">
                  <h3 className="date-header">{formatDate(date)}</h3>
                  <div className="events-list">
                    {dateEvents.map(renderEvent)}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {showNewEvent && (
          <div className="modal-overlay" onClick={() => setShowNewEvent(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <h3>New Event</h3>
              <div className="form-group">
                <label className="form-label">Event Title</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Meeting title"
                  value={newEvent.subject}
                  onChange={(e) => setNewEvent({ ...newEvent, subject: e.target.value })}
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label className="form-label">Date</label>
                <input
                  type="date"
                  className="form-input"
                  value={newEvent.date}
                  onChange={(e) => setNewEvent({ ...newEvent, date: e.target.value })}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Start Time</label>
                  <input
                    type="time"
                    className="form-input"
                    value={newEvent.startTime}
                    onChange={(e) => setNewEvent({ ...newEvent, startTime: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">End Time</label>
                  <input
                    type="time"
                    className="form-input"
                    value={newEvent.endTime}
                    onChange={(e) => setNewEvent({ ...newEvent, endTime: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Location (optional)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Meeting room or link"
                  value={newEvent.location}
                  onChange={(e) => setNewEvent({ ...newEvent, location: e.target.value })}
                />
              </div>
              <div className="modal-actions">
                <button className="btn btn-secondary" onClick={() => setShowNewEvent(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary" onClick={createEvent}>
                  Create Event
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  )
}

function LocationIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
      <circle cx="12" cy="10" r="3"/>
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="3 6 5 6 21 6"/>
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
    </svg>
  )
}

export default Calendar
