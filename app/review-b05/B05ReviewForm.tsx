'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';

type Choice = 'YES' | 'NO' | 'UNSURE' | '';
type Verdict = 'PASS' | 'FAIL' | 'UNSURE' | '';
type FormState = {
  reviewerCode: string;
  closureContinuity: string;
  twoSidedContactReadability: string;
  synchronizedTransport: string;
  visibleMeshDrift: Choice;
  visiblePop: Choice;
  overallAcceptance: Verdict;
  note: string;
  watchedTwice: boolean;
};

const initial: FormState = { reviewerCode: '', closureContinuity: '', twoSidedContactReadability: '', synchronizedTransport: '', visibleMeshDrift: '', visiblePop: '', overallAcceptance: '', note: '', watchedTwice: false };

function Scale({ name, value, onChange }: { name: keyof FormState; value: string; onChange: (name: keyof FormState, value: string) => void }) {
  return <div className="review-scale">{[1,2,3,4,5].map(score => <label key={score}><input type="radio" name={name} value={score} checked={value === String(score)} onChange={() => onChange(name, String(score))} /><span>{score}</span></label>)}</div>;
}

function Choices({ name, value, values, onChange }: { name: keyof FormState; value: string; values: string[]; onChange: (name: keyof FormState, value: string) => void }) {
  return <div className="review-choices">{values.map(choice => <label key={choice}><input type="radio" name={name} value={choice} checked={value === choice} onChange={() => onChange(name, choice)} /><span>{choice}</span></label>)}</div>;
}

export default function B05ReviewForm({ videoSrc }: { videoSrc: string }) {
  const [form, setForm] = useState<FormState>(initial);
  const [saved, setSaved] = useState(false);
  const update = (name: keyof FormState, value: string | boolean) => setForm(current => ({ ...current, [name]: value }));
  const ready = useMemo(() => /^[A-Za-z0-9_-]{3,24}$/.test(form.reviewerCode)
    && form.closureContinuity && form.twoSidedContactReadability && form.synchronizedTransport
    && form.visibleMeshDrift && form.visiblePop && form.overallAcceptance && form.watchedTwice, [form]);

  function download(event: React.FormEvent) {
    event.preventDefault();
    if (!ready) return;
    const payload = {
      documentType: 'BFS_B05_HUMAN_REVIEW_RESPONSE', protocolVersion: '0.3.0', clipId: 'CLIP_G52Q',
      clipSha256: 'f7f7c1ce3eaf36cacf8f3c5f4d143fbdcce574bfb61633b9bc9238cbc4f8cbaa',
      reviewerCode: form.reviewerCode, submittedAtUtc: new Date().toISOString(), watchedTwice: true,
      answers: {
        closureContinuity: Number(form.closureContinuity), twoSidedContactReadability: Number(form.twoSidedContactReadability),
        synchronizedTransport: Number(form.synchronizedTransport), visibleMeshDrift: form.visibleMeshDrift,
        visiblePop: form.visiblePop, overallAcceptance: form.overallAcceptance, note: form.note.trim(),
      },
      privacy: { transmitted: false, personalDataRequested: false },
    };
    const url = URL.createObjectURL(new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `CLIP_G52Q-${form.reviewerCode}.review.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setSaved(true);
  }

  return <>
    <section className="review-clip"><div><span>ANONYMOUS REVIEW ASSET</span><h1>CLIP_G52Q</h1><p>请用正常速度完整观看至少两次。提交前不要打开 B05 指标、逐帧图或实验报告。</p></div><video controls preload="metadata" playsInline aria-label="B05 匿名抓握编译审查视频"><source src={videoSrc} type="video/mp4" />浏览器无法播放此视频。</video></section>
    <form className="review-form" onSubmit={download}>
      <div className="review-intro"><span>PROTOCOL 0.3</span><h2>只判断可见的运动关系。</h2><p>这是技术夹爪，不是人手。请勿评价造型、材质或电影感；只判断闭合、双侧接触、搬运同步和释放连续性。1 表示明显失败，5 表示对技术代理而言清楚可信。</p></div>
      <label className="review-code"><span>匿名评审代码</span><input required pattern="[A-Za-z0-9_-]{3,24}" maxLength={24} value={form.reviewerCode} onChange={event => update('reviewerCode', event.target.value)} placeholder="例如 R05_P2" /><small>只允许 3–24 位字母、数字、下划线或连字符；不要填写姓名或邮箱。</small></label>
      <fieldset><legend><span>01</span>两侧手指从张开到闭合是否连续？</legend><Scale name="closureContinuity" value={form.closureContinuity} onChange={update} /><div className="review-scale-labels"><span>1 · 明显跳变</span><span>5 · 连续清楚</span></div></fieldset>
      <fieldset><legend><span>02</span>闭合后，是否清楚看到道具被两侧同时夹住？</legend><Scale name="twoSidedContactReadability" value={form.twoSidedContactReadability} onChange={update} /><div className="review-scale-labels"><span>1 · 接触不成立</span><span>5 · 双侧关系清楚</span></div></fieldset>
      <fieldset><legend><span>03</span>搬运阶段，道具与两侧手指是否同步移动？</legend><Scale name="synchronizedTransport" value={form.synchronizedTransport} onChange={update} /><div className="review-scale-labels"><span>1 · 明显脱离</span><span>5 · 始终同步</span></div></fieldset>
      <fieldset><legend><span>04</span>是否看到手指可见网格在搬运时离开其抓握位置？</legend><Choices name="visibleMeshDrift" value={form.visibleMeshDrift} values={['YES','NO','UNSURE']} onChange={update} /></fieldset>
      <fieldset><legend><span>05</span>拿起或释放瞬间是否出现可见位置跳变？</legend><Choices name="visiblePop" value={form.visiblePop} values={['YES','NO','UNSURE']} onChange={update} /></fieldset>
      <fieldset><legend><span>06</span>只针对“编译后的抓握运动是否视觉可接受”，你的判断是？</legend><Choices name="overallAcceptance" value={form.overallAcceptance} values={['PASS','FAIL','UNSURE']} onChange={update} /></fieldset>
      <label className="review-note"><span>07 · 可选失败说明</span><textarea maxLength={500} value={form.note} onChange={event => update('note', event.target.value)} placeholder="最先注意到的问题是什么？" /><small>{form.note.length} / 500</small></label>
      <label className="review-confirm"><input type="checkbox" checked={form.watchedTwice} onChange={event => update('watchedTwice', event.target.checked)} /><span>我已在未查看指标的情况下，以正常速度完整观看至少两次。</span></label>
      <button type="submit" disabled={!ready}>下载匿名评审 JSON</button>
      <p className="review-privacy">静态页面不会上传答案。请把下载的 JSON 交给研究负责人；聚合前不得修改内容。</p>
      {saved && <div className="review-saved"><b>RESPONSE SAVED LOCALLY</b><p>文件已下载。现在可以查看机器证据，不会再影响本次评分。</p><Link href="/grasp-v0-2">查看 B05 机器证据 →</Link></div>}
    </form>
  </>;
}
