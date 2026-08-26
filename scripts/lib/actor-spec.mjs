import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { repositoryRoot } from './scene-spec.mjs';

export const actorSchemaPath = resolve(repositoryRoot, 'specs/actor-spec.v0.1.schema.json');
export const actorFixturePath = resolve(repositoryRoot, 'specs/fixtures/actor-spec-fixtures.v0.1.json');

const readJson = async path => JSON.parse(await readFile(path, 'utf8'));
const schema = await readJson(actorSchemaPath);
const ajv = new Ajv2020({ allErrors: true, strict: true, formats: { 'date-time': true } });
const validateSchema = ajv.compile(schema);

function safeWorkspacePath(uri, allowedRoots) {
  const normalized = uri.replaceAll('\\', '/');
  return !normalized.startsWith('/')
    && !normalized.includes('://')
    && !normalized.split('/').includes('..')
    && allowedRoots.some(root => normalized.startsWith(root));
}

function checkOrderedKeys(keys, frameStart, frameEnd, path, add) {
  let previous = -1;
  for (const [index, key] of keys.entries()) {
    if (key.frame < frameStart || key.frame > frameEnd) {
      add('SEM_KEY_FRAME', `${path}/${index}/frame`, `Key ${key.frame} is outside the performance range`);
    }
    if (key.frame <= previous) {
      add('SEM_KEY_ORDER', `${path}/${index}/frame`, 'Keys must be strictly increasing');
    }
    previous = key.frame;
  }
}

export function actorSemanticErrors(document) {
  const errors = [];
  const add = (code, path, message) => errors.push({ code, path, message });
  const { frameStart, frameEnd } = document.performance;

  if (frameEnd < frameStart) add('SEM_FRAME_RANGE', '/performance/frameEnd', 'frameEnd must be greater than or equal to frameStart');

  const semantics = new Set();
  const targetBones = new Set();
  for (const [index, mapping] of document.rig.bones.entries()) {
    if (semantics.has(mapping.semantic)) add('SEM_DUPLICATE_BONE_SEMANTIC', `/rig/bones/${index}/semantic`, `Duplicate semantic bone ${mapping.semantic}`);
    if (targetBones.has(mapping.bone)) add('SEM_DUPLICATE_TARGET_BONE', `/rig/bones/${index}/bone`, `Target bone ${mapping.bone} is mapped twice`);
    semantics.add(mapping.semantic);
    targetBones.add(mapping.bone);
  }

  const requiredSemantics = ['ROOT', 'PELVIS', 'HEAD', 'EYE_L', 'EYE_R', 'HAND_L', 'HAND_R', 'FOOT_L', 'FOOT_R'];
  for (const semantic of requiredSemantics) {
    if (!semantics.has(semantic)) add('SEM_REQUIRED_BONE', '/rig/bones', `Required semantic bone ${semantic} is missing`);
  }

  const socketIds = new Set();
  for (const [index, socket] of document.sockets.entries()) {
    if (socketIds.has(socket.id)) add('SEM_DUPLICATE_SOCKET', `/sockets/${index}/id`, `Socket ${socket.id} is duplicated`);
    if (!semantics.has(socket.boneSemantic)) add('SEM_SOCKET_BONE', `/sockets/${index}/boneSemantic`, `Socket ${socket.id} references an unmapped semantic bone`);
    socketIds.add(socket.id);
  }

  const shapeChannels = new Set();
  const targetKeys = new Set();
  for (const [index, channel] of document.deformation.shapeChannels.entries()) {
    if (shapeChannels.has(channel.id)) add('SEM_DUPLICATE_SHAPE_CHANNEL', `/deformation/shapeChannels/${index}/id`, `Shape channel ${channel.id} is duplicated`);
    if (targetKeys.has(channel.targetKey)) add('SEM_DUPLICATE_TARGET_KEY', `/deformation/shapeChannels/${index}/targetKey`, `Shape key ${channel.targetKey} is mapped twice`);
    if (channel.minimum > channel.maximum || channel.neutral < channel.minimum || channel.neutral > channel.maximum) {
      add('SEM_SHAPE_RANGE', `/deformation/shapeChannels/${index}`, `Shape channel ${channel.id} has an invalid neutral/minimum/maximum relationship`);
    }
    shapeChannels.add(channel.id);
    targetKeys.add(channel.targetKey);
  }

  const allowedRoots = document.security.allowedRoots;
  for (const [index, [path, label]] of [[document.actor.assetUri, 'actor asset'], ...document.performance.bodyActions.map(item => [item.uri, `body action ${item.id}`])].entries()) {
    if (!safeWorkspacePath(path, allowedRoots)) add('SEC_PATH_TRAVERSAL', index === 0 ? '/actor/assetUri' : `/performance/bodyActions/${index - 1}/uri`, `${label} URI escapes allowed roots`);
  }

  const bodyActionIds = new Set();
  for (const [index, action] of document.performance.bodyActions.entries()) {
    if (bodyActionIds.has(action.id)) add('SEM_DUPLICATE_ACTION', `/performance/bodyActions/${index}/id`, `Body action ${action.id} is duplicated`);
    if (action.frameEnd < action.frameStart) add('SEM_ACTION_RANGE', `/performance/bodyActions/${index}/frameEnd`, `Body action ${action.id} has a reversed range`);
    if (action.frameStart < frameStart || action.frameEnd > frameEnd) add('SEM_ACTION_FRAME', `/performance/bodyActions/${index}`, `Body action ${action.id} is outside the performance range`);
    bodyActionIds.add(action.id);
  }

  const facialChannels = new Set();
  for (const [index, curve] of document.performance.facialCurves.entries()) {
    if (!shapeChannels.has(curve.channel)) add('SEM_FACE_CHANNEL', `/performance/facialCurves/${index}/channel`, `Facial channel ${curve.channel} is not declared`);
    if (facialChannels.has(curve.channel)) add('SEM_DUPLICATE_FACE_CURVE', `/performance/facialCurves/${index}/channel`, `Facial channel ${curve.channel} has multiple curves`);
    checkOrderedKeys(curve.keys, frameStart, frameEnd, `/performance/facialCurves/${index}/keys`, add);
    facialChannels.add(curve.channel);
  }

  checkOrderedKeys(document.performance.gazeKeys, frameStart, frameEnd, '/performance/gazeKeys', add);

  const contactIds = new Set();
  for (const [index, contact] of document.performance.contacts.entries()) {
    if (contactIds.has(contact.id)) add('SEM_DUPLICATE_CONTACT', `/performance/contacts/${index}/id`, `Contact ${contact.id} is duplicated`);
    if (!socketIds.has(contact.effectorSocket)) add('SEM_CONTACT_SOCKET', `/performance/contacts/${index}/effectorSocket`, `Contact ${contact.id} references an unknown actor socket`);
    if (contact.frameEnd < contact.frameStart) add('SEM_CONTACT_RANGE', `/performance/contacts/${index}/frameEnd`, `Contact ${contact.id} has a reversed range`);
    if (contact.frameStart < frameStart || contact.frameEnd > frameEnd) add('SEM_CONTACT_FRAME', `/performance/contacts/${index}`, `Contact ${contact.id} is outside the performance range`);
    contactIds.add(contact.id);
  }

  return errors;
}

export function validateActorSpec(document) {
  const schemaValid = validateSchema(document);
  const errors = [];
  if (!schemaValid) {
    for (const error of validateSchema.errors ?? []) {
      errors.push({ code: 'SCHEMA', path: error.instancePath || '/', message: error.message ?? 'Schema validation failed' });
    }
  } else {
    errors.push(...actorSemanticErrors(document));
  }
  return { valid: errors.length === 0, errors };
}
