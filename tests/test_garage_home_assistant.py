"""Execute the real HA tag trigger and blueprint actions, with mock door services."""
import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio
from homeassistant import loader
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA, PLATFORM_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.core import HomeAssistant
from homeassistant.helpers.script import Script, async_validate_actions_config
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import async_setup as setup_triggers, async_validate_trigger_config, async_initialize_triggers
from homeassistant.util.yaml import load_yaml

ROOT = Path(__file__).resolve().parents[1]
READER = '0123456789abcdef0123456789abcdef'
CARD = 'wg34-12345678'


@pytest_asyncio.fixture
async def rig(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    dr.async_setup(hass)
    await dr.async_load(hass, load_empty=True)
    await setup_triggers(hass)
    bp = Blueprint(load_yaml(str(ROOT / 'blueprints/GarageCardAction.yaml')),
                   expected_domain='automation', schema=AUTOMATION_BLUEPRINT_SCHEMA)
    inputs = BlueprintInputs(bp, {'use_blueprint': {'path': 'test.yaml', 'input': {
        'reader': READER, 'card_id': CARD, 'cooldown': 1,
        'access_conditions': [{'condition': 'state', 'entity_id': 'input_boolean.guest_access', 'state': 'on'}],
        'granted_actions': [{'action': 'cover.open_cover', 'target': {'entity_id': 'cover.garage_gate'}},
                            {'action': 'script.side_door'}],
    }}})
    inputs.validate()
    config = PLATFORM_SCHEMA(inputs.async_substitute())
    config['triggers'] = await async_validate_trigger_config(hass, config['triggers'])
    # Conditions normally run in HA's automation handler; use HA's real condition
    # action here before executing the unmodified blueprint action sequence.
    actions = [{'condition': 'and', 'conditions': config['conditions']}, *config['actions']]
    actions = await async_validate_actions_config(hass, actions)
    script = Script(hass, actions, 'Card rights', 'automation', script_mode=config['mode'])
    calls = []

    async def service(call):
        calls.append((call.domain, call.service, dict(call.data)))

    hass.services.async_register('cover', 'open_cover', service)
    hass.services.async_register('script', 'side_door', service)
    hass.states.async_set('input_boolean.guest_access', 'on')

    async def action(variables, context=None):
        await script.async_run(variables, context=context)

    remove = await async_initialize_triggers(hass, config['triggers'], action,
        'automation', 'Card rights', logging.getLogger(__name__).log)
    assert remove is not None

    async def scan(card=CARD, reader=READER):
        hass.bus.async_fire('tag_scanned', {'tag_id': card, 'device_id': reader})
        # Allow the async trigger/service chain to reach its cooldown timer.
        for _ in range(20):
            await asyncio.sleep(0)

    yield SimpleNamespace(hass=hass, calls=calls, scan=scan, script=script)
    remove()
    await script.async_stop()
    await hass.async_stop()


@pytest.mark.asyncio
async def test_card_is_scoped_to_assigned_reader(rig):
    await rig.scan(card='wg34-999')
    await rig.scan(reader='fedcba9876543210fedcba9876543210')
    await rig.scan(card='wg26-12345678')
    assert rig.calls == []
    await rig.scan()
    assert [f'{d}.{s}' for d, s, _ in rig.calls] == ['cover.open_cover', 'script.side_door']
    assert rig.calls[0][2]['entity_id'] == ['cover.garage_gate']


@pytest.mark.asyncio
async def test_repeat_is_dropped_and_later_presentation_works(rig):
    await rig.scan()
    assert len(rig.calls) == 2
    await rig.scan()
    assert len(rig.calls) == 2
    await asyncio.sleep(1.1)
    await rig.scan()
    assert len(rig.calls) == 4


@pytest.mark.asyncio
async def test_access_condition_blocks_actions(rig):
    rig.hass.states.async_set('input_boolean.guest_access', 'off')
    await rig.scan()
    assert rig.calls == []
    rig.hass.states.async_set('input_boolean.guest_access', 'on')
    await rig.scan()
    assert len(rig.calls) == 2


@pytest.mark.asyncio
async def test_diagnostic_reconnect_state_never_triggers_access(rig):
    rig.hass.states.async_set('sensor.garage_card_reader_last_card', 'unavailable')
    rig.hass.states.async_set('sensor.garage_card_reader_last_card', CARD)
    await rig.hass.async_block_till_done()
    assert rig.calls == []

