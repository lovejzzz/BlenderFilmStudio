'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';

type Choice = 'YES' | 'NO' | 'UNSURE' | '';
type Verdict = 'PASS' | 'FAIL' | 'UNSURE' | '';
type FormState = { reviewerCode: string; twoSidedSupport: string; transportSynchronization: string; releasePlausibility: string; visibleInterpenetration: Choice; visiblePop: Choice; overallAcceptance: Verdict; note: string; watchedTwice: boolean };
const initial: FormState = { reviewerCode: '', twoSidedSupport: '', transportSynchronization: '', releasePlausibility: '', visibleInterpenetration: '', visiblePop: '', overallAcceptance: '', note: '', watchedTwice: false };

function Scale({ name, value, onChange }: { name: keyof FormState; value: string; onChange: (name: keyof FormState, value: string) => void }) {
  return <div className="review-scale">{[1,2,3,4,5].map(score => <label key={score}><input type="radio" name={name} value={score} checked={value === String(score)} onChange={() => onChange(name, String(score))} /><span>{score}</span></label>)}</div>;
}
function Choices({ name, value, values, onChange }: { name: keyof FormState; value: string; values: string[]; onChange: (name: keyof FormState, value: string) => void }) {
  return <div className="review-choices">{values.map(choice => <label key={choice}><input type="radio" name={name} value={choice} checked={value === choice} onChange={() => onChange(name, choice)} /><span>{choice}</span></label>)}</div>;
}

export default function B06ReviewForm({ videoSrc }: { videoSrc: string }) {
  const [form, setForm] = useState<FormState>(initial);
  const [saved, setSaved] = useState(false);
  const update = (name: keyof FormState, value: string | boolean) => setForm(current => ({ ...current, [name]: value }));
  const ready = useMemo(() => /^[A-Za-z0-9_-]{3,24}$/.test(form.reviewerCode) && form.twoSidedSupport && form.transportSynchronization && form.releasePlausibility && form.visibleInterpenetration && form.visiblePop && form.overallAcceptance && form.watchedTwice, [form]);
  function download(event: React.FormEvent) {
    event.preventDefault();
    if (!ready) return;
    const payload = {
      documentType: 'BFS_B09_SOURCE_PHYSICS_REVIEW_RESPONSE', protocolVersion: '0.4.0', clipId: 'CLIP_P84R', clipSha256: '244974d7be08107e9b88ab855a05fbfdeda486f52d66076fd29581305fe35041',
      reviewerCode: form.reviewerCode, submittedAtUtc: new Date().toISOString(), watchedTwice: true,
      answers: { twoSidedSupport: Number(form.twoSidedSupport), transportSynchronization: Number(form.transportSynchronization), releasePlausibility: Number(form.releasePlausibility), visibleInterpenetration: form.visibleInterpenetration, visiblePop: form.visiblePop, overallAcceptance: form.overallAcceptance, note: form.note.trim() },
      privacy: { transmitted: false, personalDataRequested: false },
    };
    const url = URL.createObjectURL(new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: 'application/json' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `CLIP_P84R-${form.reviewerCode}.review.json`; anchor.click(); URL.revokeObjectURL(url); setSaved(true);
  }
  return <>
    <section className="review-clip"><div><span>ANONYMOUS REVIEW ASSET</span><h1>CLIP_P84R</h1><p>请用正常速度完整观看至少两次。提交前不要打开 B06/B07/B08 指标、逐帧图或实验报告。</p></div><video controls preload="metadata" playsInline aria-label="匿名双侧刚体支撑与释放审查视频"><source src={videoSrc} type="video/mp4" />浏览器无法播放此视频。</video></section>
    <form className="review-form" onSubmit={download}>
      <div className="review-intro"><span>PROTOCOL 0.4</span><h2>只判断可见的物理关系。</h2><p>这是低细节技术代理。请勿评价造型、材质或电影感；只判断双侧支撑、竖直搬运同步和释放起始是否可信。1 表示明显失败，5 表示对该技术代理而言清楚可信。</p></div>
      <label className="review-code"><span>匿名评审代码</span><input required pattern="[A-Za-z0-9_-]{3,24}" maxLength={24} value={form.reviewerCode} onChange={event => update('reviewerCode', event.target.value)} placeholder="例如 P84_R2" /><small>只允许 3–24 位字母、数字、下划线或连字符；不要填写姓名或邮箱。</small></label>
      <fieldset><legend><span>01</span>保持阶段，道具是否清楚地由两侧共同支撑？</legend><Scale name="twoSidedSupport" value={form.twoSidedSupport} onChange={update} /><div className="review-scale-labels"><span>1 · 支撑不成立</span><span>5 · 双侧支撑清楚</span></div></fieldset>
      <fieldset><legend><span>02</span>竖直搬运时，道具是否与两侧碰撞体同步且无滑脱？</legend><Scale name="transportSynchronization" value={form.transportSynchronization} onChange={update} /><div className="review-scale-labels"><span>1 · 明显漂移</span><span>5 · 同步可信</span></div></fieldset>
      <fieldset><legend><span>03</span>两侧打开后，道具开始下落的运动是否符合直觉？</legend><Scale name="releasePlausibility" value={form.releasePlausibility} onChange={update} /><div className="review-scale-labels"><span>1 · 明显不自然</span><span>5 · 释放可信</span></div></fieldset>
      <fieldset><legend><span>04</span>是否看到明显穿透，或未接触却悬空跟随？</legend><Choices name="visibleInterpenetration" value={form.visibleInterpenetration} values={['YES','NO','UNSURE']} onChange={update} /></fieldset>
      <fieldset><legend><span>05</span>闭合、搬运或释放时是否出现可见跳变/瞬移？</legend><Choices name="visiblePop" value={form.visiblePop} values={['YES','NO','UNSURE']} onChange={update} /></fieldset>
      <fieldset><legend><span>06</span>只针对“这条可见源轨迹是否物理可信”，你的判断是？</legend><Choices name="overallAcceptance" value={form.overallAcceptance} values={['PASS','FAIL','UNSURE']} onChange={update} /></fieldset>
      <label className="review-note"><span>07 · 可选失败说明</span><textarea maxLength={500} value={form.note} onChange={event => update('note', event.target.value)} placeholder="最先注意到的问题是什么？" /><small>{form.note.length} / 500</small></label>
      <label className="review-confirm"><input type="checkbox" checked={form.watchedTwice} onChange={event => update('watchedTwice', event.target.checked)} /><span>我已在未查看指标的情况下，以正常速度完整观看至少两次。</span></label>
      <button type="submit" disabled={!ready}>下载匿名评审 JSON</button><p className="review-privacy">静态页面不会上传答案。请把下载的 JSON 交给研究负责人；聚合前不得修改内容。</p>
      {saved && <div className="review-saved"><b>RESPONSE SAVED LOCALLY</b><p>文件已下载。现在可以查看机器证据，不会再影响本次评分。</p><Link href="/physics-v0-1">查看 B06 机器证据 →</Link></div>}
    </form>
  </>;
}
