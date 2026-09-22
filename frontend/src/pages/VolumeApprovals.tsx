import { FormEvent, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useCurrentUser } from '../hooks/useCurrentUser'
import type { Pond, VolumeChangeRequest, VolumeChangeStatus } from '../types'

const STATUS_LABEL: Record<VolumeChangeStatus, string> = {
  pending: '待审',
  approved: '通过',
  rejected: '驳回',
}

const empty = {
  pondId: 0,
  requestedVolumeM3: 0,
  reason: '',
}

export default function VolumeApprovals() {
  const [searchParams] = useSearchParams()
  const user = useCurrentUser()
  const isTechnician = user?.role === 'technician'
  const isAdmin = user?.role === 'admin'

  const [ponds, setPonds] = useState<Pond[]>([])
  const [rows, setRows] = useState<VolumeChangeRequest[]>([])
  const [filter, setFilter] = useState<'all' | VolumeChangeStatus>('all')
  const [form, setForm] = useState(empty)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function load() {
    const [ps, rs] = await Promise.all([
      api<Pond[]>('/api/ponds'),
      api<VolumeChangeRequest[]>('/api/volume-change-requests'),
    ])
    setPonds(ps)
    setRows(rs)
    const qp = Number(searchParams.get('pondId'))
    setForm((f) => ({
      ...f,
      pondId: f.pondId || qp || ps[0]?.id || 0,
      requestedVolumeM3:
        f.requestedVolumeM3 ||
        (qp ? ps.find((p) => p.id === qp)?.volumeM3 ?? 0 : 0),
    }))
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const pondOf = (id: number) => ponds.find((p) => p.id === id)
  const pondLabel = (r: VolumeChangeRequest) =>
    r.pondCode
      ? `${r.pondCode}（#${r.pondId}）`
      : `塘口 #${r.pondId}`

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setNotice('')
    try {
      await api('/api/volume-change-requests', {
        method: 'POST',
        body: JSON.stringify({
          pondId: form.pondId,
          requestedVolumeM3: Number(form.requestedVolumeM3),
          reason: form.reason,
        }),
      })
      setForm((f) => ({ ...empty, pondId: f.pondId }))
      setNotice('申请已提交，等待场长审批')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '申请失败')
    }
  }

  async function review(id: number, action: 'approve' | 'reject') {
    setError('')
    setNotice('')
    let comment = ''
    if (action === 'reject') {
      const input = prompt('驳回理由（可留空）')
      if (input === null) return // 用户取消
      comment = input
    }
    try {
      await api(`/api/volume-change-requests/${id}/${action}`, {
        method: 'POST',
        body: JSON.stringify({ comment: comment || null }),
      })
      setNotice(action === 'approve' ? '已通过，塘口体积已更新' : '已驳回，塘口体积不变')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '审批失败')
    }
  }

  const shown = rows.filter((r) => filter === 'all' || r.status === filter)

  return (
    <div>
      <header className="page-header">
        <h1>塘口体积变更审批</h1>
        <p className="muted">
          塘口体积不允许直接修改；技术员发起变更申请，场长审批通过后体积同事务生效，驳回则不变。
          同一塘口同时只允许一张待审单。
        </p>
      </header>
      {error && <div className="error">{error}</div>}
      {notice && <div className="notice">{notice}</div>}

      {isTechnician && (
        <form className="panel form-grid" onSubmit={onSubmit}>
          <label>
            申请塘口
            <select
              value={form.pondId}
              onChange={(e) => {
                const pid = Number(e.target.value)
                setForm({
                  ...form,
                  pondId: pid,
                  requestedVolumeM3: pondOf(pid)?.volumeM3 ?? 0,
                })
              }}
              required
            >
              <option value={0} disabled>
                请选择塘口
              </option>
              {ponds.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.pondCode}（当前 {p.volumeM3} m³）
                </option>
              ))}
            </select>
          </label>
          <label>
            申请体积 (m³，正数且与原体积不同)
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
            理由（去空白至少 6 个字）
            <input
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
              placeholder="例如：清淤后实测蓄水深度变化，申请重新核定体积"
              required
            />
          </label>
          <button type="submit" className="btn primary">
            发起体积变更申请
          </button>
        </form>
      )}

      <div className="filter-bar">
        {(['all', 'pending', 'approved', 'rejected'] as const).map((s) => (
          <button
            key={s}
            className={`btn ghost filter-btn ${filter === s ? 'active' : ''}`}
            onClick={() => setFilter(s)}
          >
            {s === 'all' ? '全部' : STATUS_LABEL[s]}
          </button>
        ))}
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>塘口</th>
              <th>原体积 m³</th>
              <th>申请体积 m³</th>
              <th>理由</th>
              <th>状态</th>
              <th>申请人</th>
              <th>审批人</th>
              <th>审批意见</th>
              {isAdmin && <th>操作</th>}
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{pondLabel(r)}</td>
                <td>{r.originalVolumeM3}</td>
                <td>{r.requestedVolumeM3}</td>
                <td>{r.reason}</td>
                <td>
                  <span className={`badge vcr-${r.status}`}>
                    {STATUS_LABEL[r.status]}
                  </span>
                </td>
                <td>{r.applicantName || `#${r.applicantId}`}</td>
                <td>{r.approverName || '—'}</td>
                <td>{r.reviewComment || '—'}</td>
                {isAdmin && (
                  <td>
                    {r.status === 'pending' ? (
                      <div className="row-actions">
                        <button
                          className="btn primary small"
                          onClick={() => review(r.id, 'approve')}
                        >
                          通过
                        </button>
                        <button
                          className="btn danger small"
                          onClick={() => review(r.id, 'reject')}
                        >
                          驳回
                        </button>
                      </div>
                    ) : (
                      <span className="muted">已终态</span>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {shown.length === 0 && (
              <tr>
                <td colSpan={isAdmin ? 10 : 9} className="muted center">
                  暂无审批单
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
