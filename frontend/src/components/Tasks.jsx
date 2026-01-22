import { useState, useEffect } from 'react'
import './Tasks.css'

const API_BASE = 'http://localhost:8000'

function Tasks() {
  const [taskLists, setTaskLists] = useState([])
  const [activeList, setActiveList] = useState(null)
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCompleted, setShowCompleted] = useState(false)
  const [showNewTask, setShowNewTask] = useState(false)
  const [newTaskTitle, setNewTaskTitle] = useState('')

  useEffect(() => {
    loadTaskLists()
  }, [])

  useEffect(() => {
    if (activeList) {
      loadTasks(activeList.id)
    }
  }, [activeList, showCompleted])

  const loadTaskLists = async () => {
    try {
      const res = await fetch(`${API_BASE}/tasks/lists`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        const lists = data.lists || []
        setTaskLists(lists)

        // Set default list as active
        const defaultList = lists.find(l => l.is_default) || lists[0]
        if (defaultList) {
          setActiveList(defaultList)
        }
      }
    } catch (error) {
      console.error('Failed to load task lists:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadTasks = async (listId) => {
    setLoading(true)
    try {
      const res = await fetch(
        `${API_BASE}/tasks/list/${listId}?include_completed=${showCompleted}`,
        { credentials: 'include' }
      )
      if (res.ok) {
        const data = await res.json()
        setTasks(data.tasks || [])
      }
    } catch (error) {
      console.error('Failed to load tasks:', error)
    } finally {
      setLoading(false)
    }
  }

  const createTask = async () => {
    if (!newTaskTitle.trim() || !activeList) return

    try {
      const res = await fetch(`${API_BASE}/tasks/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          title: newTaskTitle,
          list_id: activeList.id,
        }),
      })

      if (res.ok) {
        setNewTaskTitle('')
        setShowNewTask(false)
        loadTasks(activeList.id)
      }
    } catch (error) {
      console.error('Failed to create task:', error)
    }
  }

  const completeTask = async (task) => {
    try {
      const res = await fetch(
        `${API_BASE}/tasks/complete/${activeList.id}/${task.id}`,
        {
          method: 'POST',
          credentials: 'include',
        }
      )

      if (res.ok) {
        loadTasks(activeList.id)
      }
    } catch (error) {
      console.error('Failed to complete task:', error)
    }
  }

  const deleteTask = async (task) => {
    if (!confirm('Delete this task?')) return

    try {
      const res = await fetch(
        `${API_BASE}/tasks/delete/${activeList.id}/${task.id}`,
        {
          method: 'DELETE',
          credentials: 'include',
        }
      )

      if (res.ok) {
        loadTasks(activeList.id)
      }
    } catch (error) {
      console.error('Failed to delete task:', error)
    }
  }

  const formatDueDate = (dateStr) => {
    if (!dateStr) return null
    const date = new Date(dateStr)
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)

    if (date < today) {
      return { text: 'Overdue', class: 'overdue' }
    } else if (date.toDateString() === today.toDateString()) {
      return { text: 'Today', class: 'today' }
    } else if (date.toDateString() === tomorrow.toDateString()) {
      return { text: 'Tomorrow', class: 'tomorrow' }
    }

    return {
      text: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      class: '',
    }
  }

  return (
    <>
      <div className="content-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Tasks</h2>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={showCompleted}
                onChange={(e) => setShowCompleted(e.target.checked)}
              />
              <span>Show completed</span>
            </label>
            <button className="btn btn-primary" onClick={() => setShowNewTask(true)}>
              Add Task
            </button>
          </div>
        </div>
      </div>

      <div className="content-body">
        <div className="tasks-layout">
          <div className="task-lists">
            {taskLists.map((list) => (
              <button
                key={list.id}
                className={`task-list-item ${activeList?.id === list.id ? 'active' : ''}`}
                onClick={() => setActiveList(list)}
              >
                <ListIcon />
                {list.name}
              </button>
            ))}
          </div>

          <div className="tasks-container">
            {loading ? (
              <div className="loading">
                <div className="loading-spinner"></div>
              </div>
            ) : tasks.length === 0 ? (
              <div className="empty-state">
                <h3>No tasks</h3>
                <p>{showCompleted ? 'No tasks in this list' : 'All caught up!'}</p>
              </div>
            ) : (
              <div className="task-items">
                {tasks.map((task) => {
                  const dueInfo = formatDueDate(task.due_date)
                  return (
                    <div
                      key={task.id}
                      className={`task-item ${task.status === 'completed' ? 'completed' : ''}`}
                    >
                      <button
                        className="task-checkbox"
                        onClick={() => completeTask(task)}
                        disabled={task.status === 'completed'}
                      >
                        {task.status === 'completed' ? <CheckIcon /> : null}
                      </button>
                      <div className="task-content">
                        <div className="task-title">{task.title}</div>
                        {task.body && <div className="task-body">{task.body}</div>}
                        {dueInfo && (
                          <span className={`task-due ${dueInfo.class}`}>
                            {dueInfo.text}
                          </span>
                        )}
                      </div>
                      <button className="task-delete" onClick={() => deleteTask(task)}>
                        <TrashIcon />
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {showNewTask && (
          <div className="modal-overlay" onClick={() => setShowNewTask(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <h3>New Task</h3>
              <div className="form-group">
                <label className="form-label">Task Title</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="What needs to be done?"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && createTask()}
                  autoFocus
                />
              </div>
              <div className="modal-actions">
                <button className="btn btn-secondary" onClick={() => setShowNewTask(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary" onClick={createTask}>
                  Add Task
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  )
}

function ListIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="8" y1="6" x2="21" y2="6"/>
      <line x1="8" y1="12" x2="21" y2="12"/>
      <line x1="8" y1="18" x2="21" y2="18"/>
      <line x1="3" y1="6" x2="3.01" y2="6"/>
      <line x1="3" y1="12" x2="3.01" y2="12"/>
      <line x1="3" y1="18" x2="3.01" y2="18"/>
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
      <polyline points="20 6 9 17 4 12"/>
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

export default Tasks
