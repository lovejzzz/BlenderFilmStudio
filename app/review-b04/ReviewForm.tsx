'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';

type Ternary = 'YES' | 'NO' | 'UNSURE' | '';
type Verdict = 'PASS' | 'FAIL' | 'UNSURE' | '';
type FormState = {
  reviewerCode: string;
  approachNaturalness: string;
  supportReadability: string;
  distractingIntersection: Ternary;
  visiblePop: Ternary;
  weightCoherence: string;
  overallAcceptance: Verdict;
  note: string;
  watchedTwice: boolean;
};

const initial: FormState = { reviewerCode: '', approachNaturalness: '', supportReadability: '', distractingIntersection: '', visiblePop: '', weightCoherence: '', overallAcceptance: '', note: '', watchedTwice: false };

function Scale({ name, value, onChange }: { name: keyof FormState; value: string; onChange: (name: keyof FormState, value: string) => void }) {
  return <div className="review-scale">{[1,2,3,4,5].map(score => <label key={score}><input type="radio" name={name} value={score} checked={value === String(score)} onChange={() => onChange(name, String(score))} /><span>{score}</span></label>)}</div>;
}

function Choice({ name, value, values, onChange }: { name: keyof FormState; value: string; values: string[]; onChange: (name: keyof FormState, value: string) => void }) {
  return <div className="review-choices">{values.map(choice => <label key={choice}><input type="radio" name={name} value={choice} checked={value === choice} onChange={() => onChange(name, choice)} /><span>{choice}</span></label>)}</div>;
}

type ReviewFormProps = { videoSrc: string; clipId: string; protocolVersion: string; evidenceHref: string };

export default function ReviewForm({ videoSrc, clipId, protocolVersion, evidenceHref }: ReviewFormProps) {
  const [form, setForm] = useState<FormState>(initial);
  const [saved, setSaved] = useState(false);
  const update = (name: keyof FormState, value: string | boolean) => setForm(current => ({ ...current, [name]: value }));
  const ready = useMemo(() => /^[A-Za-z0-9_-]{3,24}$/.test(form.reviewerCode)
    && form.approachNaturalness && form.supportReadability && form.distractingIntersection
    && form.visiblePop && form.weightCoherence && form.overallAcceptance && form.watchedTwice, [form]);

  function download(event: React.FormEvent) {
    event.preventDefault();
    if (!ready) return;
    const payload = {
      documentType: 'BFS_HUMAN_REVIEW_RESPONSE', protocolVersion, clipId,
      reviewerCode: form.reviewerCode, submittedAtUtc: new Date().toISOString(), watchedTwice: true,
      answers: {
        approachNaturalness: Number(form.approachNaturalness), supportReadability: Number(form.supportReadability),
        distractingIntersection: form.distractingIntersection, visiblePop: form.visiblePop,
        weightCoherence: Number(form.weightCoherence), overallAcceptance: form.overallAcceptance, note: form.note.trim(),
      },
      privacy: { transmitted: false, personalDataRequested: false },
    };
    const url = URL.createObjectURL(new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${clipId}-${form.reviewerCode}.review.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setSaved(true);
  }

  return <>
    <section className="review-clip"><div><span>ANONYMOUS REVIEW ASSET</span><h1>{clipId}</h1><p>请先以正常速度完整观看至少两次。不要逐帧暂停，也不要在提交前打开任何相关指标或实验报告。</p></div><video controls preload="metadata" playsInline aria-label="匿名交互审查视频"><source src={videoSrc} type="video/mp4" />浏览器无法播放此视频。</video></section>
    <form className="review-form" onSubmit={download}>
      <div className="review-intro"><span>PROTOCOL {protocolVersion.replace(/\.0$/, '')}</span><h2>只判断你看到的交互。</h2><p>角色是技术代理。请判断动作关系，不评价造型是否好看。1 表示明显失败，5 表示对这个技术代理而言清楚可信。</p></div>
      <label className="review-code"><span>匿名评审代码</span><input required pattern="[A-Za-z0-9_-]{3,24}" maxLength={24} value={form.reviewerCode} onChange={event => update('reviewerCode', event.target.value)} placeholder="例如 R03_K7" /><small>只允许 3–24 位字母、数字、下划线或连字符；不要填写姓名或邮箱。</small></label>
      <fieldset><legend><span>01</span>手部接近物体的过程是否连续、像有意图？</legend><Scale name="approachNaturalness" value={form.approachNaturalness} onChange={update} /><div className="review-scale-labels"><span>1 · 明显跳变</span><span>5 · 连续自然</span></div></fieldset>
      <fieldset><legend><span>02</span>持有和搬运时，物体看起来被手支撑了吗？</legend><Scale name="supportReadability" value={form.supportReadability} onChange={update} /><div className="review-scale-labels"><span>1 · 没有支撑关系</span><span>5 · 支撑关系清楚</span></div></fieldset>
      <fieldset><legend><span>03</span>是否看到令人分心的手—物体穿插？</legend><Choice name="distractingIntersection" value={form.distractingIntersection} values={['YES','NO','UNSURE']} onChange={update} /></fieldset>
      <fieldset><legend><span>04</span>拿起或释放瞬间是否出现可见跳变？</legend><Choice name="visiblePop" value={form.visiblePop} values={['YES','NO','UNSURE']} onChange={update} /></fieldset>
      <fieldset><legend><span>05</span>物体的重量和运动关系是否连贯？</legend><Scale name="weightCoherence" value={form.weightCoherence} onChange={update} /><div className="review-scale-labels"><span>1 · 漂浮 / 失重</span><span>5 · 重量关系可信</span></div></fieldset>
      <fieldset><legend><span>06</span>只针对“视觉交互是否可接受”，你的总体判断是？</legend><Choice name="overallAcceptance" value={form.overallAcceptance} values={['PASS','FAIL','UNSURE']} onChange={update} /></fieldset>
      <label className="review-note"><span>07 · 可选失败说明</span><textarea maxLength={500} value={form.note} onChange={event => update('note', event.target.value)} placeholder="最先注意到的问题是什么？" /><small>{form.note.length} / 500</small></label>
      <label className="review-confirm"><input type="checkbox" checked={form.watchedTwice} onChange={event => update('watchedTwice', event.target.checked)} /><span>我已在未查看指标的情况下，以正常速度完整观看至少两次。</span></label>
      <button type="submit" disabled={!ready}>下载匿名评审 JSON</button>
      <p className="review-privacy">静态页面不会上传答案。请把下载的 JSON 交给研究负责人；聚合前不得修改内容。</p>
      {saved && <div className="review-saved"><b>RESPONSE SAVED LOCALLY</b><p>文件已下载。现在可以查看实验指标，不会再影响本次评分。</p><Link href={evidenceHref}>查看 B04 机器证据 →</Link></div>}
    </form>
  </>;
}
