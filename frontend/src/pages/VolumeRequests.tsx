import { FormEvent, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, getUser } from '../api/client'
import type { Hatchery, Pond, VolumeChangeRequest } from '../types'

const empty = {
  pondId: 0,
  requestedVolumeM3: 0,
  reason: '',
}

const statusLabel: Record<VolumeChangeRequest['status'], string> = {
  pending: '待审',
  approved: '已通过',
  rejected: '已驳回',
}

const statusBadge: Record<VolumeChangeRequest['status'], string> = {
  pending: 'badge quarantine',
  approved: 'badge stocked',
  rejected: 'badge dry',
}

export default function VolumeRequests() {
  const [params] = useSearchParams()
  const [ponds, setPonds] = useState<Pond[]>([])
  const [hatcheries, setHatcheries] = useState<Hatchery[]>([])
  const [rows, setRows] = useState<VolumeChangeRequest[]>([])
  const [form, setForm] = useState(empty)
  const [error, setError] = useState('')
  const user = getUser()
  const isAdmin = user?.role === 'admin'

  async function load() {
    const [hs, ps, rs] = await Promise.all([
      api<Hatchery[]>('/api/hatcheries'),
      api<Pond[]>('/api/ponds'),
      api<VolumeChangeRequest[]>('/api/volume-change-requests'),
    ])
    setHatcheries(hs)
    setPonds(ps)
    setRows(rs)
    const queryPond = Number(params.get('pondId'))
    setForm((f) =>
      f.pondId
        ? f
        : {
            pondId: queryPond || ps[0]?.id || 0,
            requestedVolumeM3: 0,
            reason: '',
          },
    )
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  const selectedPond = ponds.find((p) => p.id === form.pondId)
  const pendingPondIds = new Set(
    rows.filter((r) => r.status === 'pending').map((r) => r.pondId),
  )

  const pondLabel = (id: number) => {
    const p = ponds.find((x) => x.id === id)
    if (!p) return `#${id}`
    const h = hatcheries.find((x) => x.id === p.hatcheryId)
    return `${h ? h.name + ' / ' : ''}${p.pondCode}`
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await api('/api/volume-change-requests', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      setForm({ ...empty, pondId: form.pondId })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败')
    }
  }

  async function decide(id: number, action: 'approve' | 'reject') {
    setError('')
    try {
      await api(`/api/volume-change-requests/${id}/${action}`, { method: 'POST' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '审批失败')
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>塘口体积变更审批</h1>
        <p className="muted">
          塘口体积不允许直接修改，须由技术员发起审批单、场长通过后生效；同塘同时仅一张待审单
        </p>
      </header>
      {error && <div className="error">{error}</div>}

      <form className="panel form-grid" onSubmit={onSubmit}>
        <label>
          所属塘口
          <select
            value={form.pondId}
            onChange={(e) =>
              setForm({ ...form, pondId: Number(e.target.value), requestedVolumeM3: 0 })
            }
            required
          >
            {ponds.map((p) => (
              <option key={p.id} value={p.id}>
                {pondLabel(p.id)}（当前 {p.volumeM3} m³）
              </option>
            ))}
          </select>
        </label>
        <label>
          申请体积 (m³，须为正且与原体积不同)
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={form.requestedVolumeM3 || ''}
            onChange={(e) =>
              setForm({ ...form, requestedVolumeM3: Number(e.target.value) })
            }
            required
          />
        </label>
        <label className="span-2">
          理由（去空白至少 6 字）
          <input
            value={form.reason}
            onChange={(e) => setForm({ ...form, reason: e.target.value })}
            required
          />
        </label>
        <button
          type="submit"
          className="btn primary"
          disabled={!!selectedPond && pendingPondIds.has(selectedPond.id)}
        >
          {selectedPond && pendingPondIds.has(selectedPond.id)
            ? '该塘已有待审单'
            : '发起体积变更申请'}
        </button>
      </form>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>所属塘口</th>
              <th>原体积 m³</th>
              <th>申请体积 m³</th>
              <th>理由</th>
              <th>状态</th>
              <th>申请人</th>
              <th>审批人</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{pondLabel(r.pondId)}</td>
                <td>{r.originalVolumeM3}</td>
                <td>{r.requestedVolumeM3}</td>
                <td>{r.reason}</td>
                <td>
                  <span className={statusBadge[r.status]}>{statusLabel[r.status]}</span>
                </td>
                <td>{r.applicantName || `#${r.applicantId}`}</td>
                <td>{r.approverName || '—'}</td>
                <td>
                  {isAdmin && r.status === 'pending' && (
                    <>
                      <button
                        className="btn primary"
                        style={{ marginRight: 8 }}
                        onClick={() => decide(r.id, 'approve')}
                      >
                        通过
                      </button>
                      <button className="btn ghost" onClick={() => decide(r.id, 'reject')}>
                        驳回
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
