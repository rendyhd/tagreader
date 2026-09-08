"""Run the actual blueprint through Home Assistant, with simulated Kodi services."""
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio

from homeassistant import loader
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA, PLATFORM_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.script import Script, async_validate_actions_config
from homeassistant.helpers.trigger import async_setup as setup_triggers, async_validate_trigger_config, async_initialize_triggers
from homeassistant.util.yaml import load_yaml

ROOT = Path(__file__).resolve().parents[1]
TAG = 'sensor.movie_time_selected_tag'
PLAYER = 'media_player.kodi'
SESSION = 'input_text.movie_time_active_tag'
INPUTS = {
    'tag_sensor': TAG,
    'play_button': 'binary_sensor.movie_time_play_button',
    'pause_button': 'binary_sensor.movie_time_pause_button',
    'stop_button': 'binary_sensor.movie_time_stop_button',
    'kodi_player': PLAYER,
    'session_helper': SESSION,
    'movies': {'movie-a': {'movieid': 123}, 'movie-b': {'file': 'smb://server/B.mkv'}},
}


@pytest_asyncio.fixture
async def rig(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    await setup_triggers(hass)
    data = load_yaml(str(ROOT / 'blueprints/MovieTimeKodi.yaml'))
    bp = Blueprint(data, expected_domain='automation', schema=AUTOMATION_BLUEPRINT_SCHEMA)
    bp_inputs = BlueprintInputs(bp, {'use_blueprint': {'path': 'test.yaml', 'input': INPUTS}})
    bp_inputs.validate()
    config = PLATFORM_SCHEMA(bp_inputs.async_substitute())
    config['triggers'] = await async_validate_trigger_config(hass, config['triggers'])
    config['actions'] = await async_validate_actions_config(hass, config['actions'])
    calls = []
    control = SimpleNamespace(fail_open=False, fail_stop=False, silent_stop_failure=False, open_gate=None)

    async def service(call):
        calls.append((call.domain, call.service, dict(call.data)))
        if call.domain == 'kodi':
            if control.open_gate:
                await control.open_gate.wait()
            if control.fail_open:
                raise HomeAssistantError('simulated Kodi transport failure')
            hass.states.async_set(PLAYER, 'playing')
        elif call.service == 'set_value':
            hass.states.async_set(SESSION, call.data['value'])
        elif call.service == 'media_stop':
            if control.fail_stop:
                raise HomeAssistantError('simulated Kodi transport failure')
            if control.silent_stop_failure:
                return  # Kodi's command wrapper can log and swallow an exception.
            hass.states.async_set(PLAYER, 'idle')
        elif call.service == 'media_pause':
            hass.states.async_set(PLAYER, 'paused')
        elif call.service == 'media_play':
            hass.states.async_set(PLAYER, 'playing')

    for domain, names in {'kodi': ['call_method'], 'input_text': ['set_value'],
                          'media_player': ['media_stop', 'media_pause', 'media_play']}.items():
        for name in names:
            hass.services.async_register(domain, name, service)

    script = Script(hass, config['actions'], 'Movie Time', 'automation',
                    script_mode=config['mode'], max_runs=config['max'])

    def states(tag='movie-a', active='', player='idle'):
        hass.states.async_set(TAG, tag)
        hass.states.async_set(SESSION, active)
        hass.states.async_set(PLAYER, player)

    async def run(kind='selection', before='', after=None, failed_item=None):
        if after is None:
            after = hass.states.get(TAG).state
        trigger = {'id': kind,
                   'from_state': None if before is None else State(TAG, before),
                   'to_state': State(TAG, after)}
        if kind == 'open_error':
            if failed_item is None:
                failed_item = INPUTS['movies'].get(hass.states.get(SESSION).state, {})
            trigger['event'] = SimpleNamespace(data={'input': {'method': 'Player.Open',
                                                              'params': {'item': failed_item}}})
        await script.async_run({'trigger': trigger}, context=Context())

    states()
    yield SimpleNamespace(hass=hass, calls=calls, control=control, script=script,
                          config=config, states=states, run=run)
    await script.async_stop()
    await hass.async_stop()


def service_names(rig):
    return [f'{domain}.{service}' for domain, service, _ in rig.calls]


@pytest.mark.asyncio
async def test_insert_pause_resume_stop_play_remove(rig):
    await rig.run()
    assert rig.calls[1][2]['item'] == {'movieid': 123}
    assert rig.calls[1][2]['options'] == {'resume': False}
    assert rig.hass.states.get(SESSION).state == 'movie-a'
    await rig.run('pause')
    await rig.run('pause')
    assert service_names(rig).count('media_player.media_pause') == 1
    await rig.run('play')
    await rig.run('play')
    assert service_names(rig).count('media_player.media_play') == 1
    await rig.run('stop')
    assert rig.hass.states.get(SESSION).state == ''
    await rig.run('selection', before='movie-a')
    assert service_names(rig).count('kodi.call_method') == 1
    await rig.run('play')
    assert service_names(rig).count('kodi.call_method') == 2
    rig.hass.states.async_set(TAG, '')
    await rig.run('selection', before='movie-a')
    assert rig.hass.states.get(PLAYER).state == 'idle'
    assert rig.hass.states.get(SESSION).state == ''


@pytest.mark.asyncio
@pytest.mark.parametrize('before', [None, 'unknown', 'unavailable'])
async def test_initial_state_never_autoplays(rig, before):
    await rig.run(before=before)
    assert rig.calls == []


@pytest.mark.asyncio
async def test_reconnect_held_case_does_not_restart(rig):
    rig.states(active='movie-a', player='playing')
    await rig.run(before='unavailable')
    assert rig.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize('tag', ['', 'movie-b', 'not-mapped'])
async def test_case_changed_during_disconnect_stops_without_autoplay(rig, tag):
    rig.states(tag=tag, active='movie-a', player='playing')
    await rig.run(before='unavailable')
    assert service_names(rig) == ['media_player.media_stop', 'input_text.set_value']


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['offline', 'startup', 'kodi_reconnected'])
async def test_outage_and_restart_stop_owned_session(rig, kind):
    rig.states(active='movie-a', player='playing')
    await rig.run(kind)
    assert rig.hass.states.get(SESSION).state == ''
    assert rig.hass.states.get(PLAYER).state == 'idle'


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['stop', 'pause', 'offline', 'startup', 'kodi_reconnected'])
async def test_does_not_control_unowned_playback(rig, kind):
    rig.states(tag='', active='', player='playing')
    await rig.run(kind)
    assert rig.calls == []


@pytest.mark.asyncio
async def test_direct_swap_opens_new_movie(rig):
    rig.states(tag='movie-b', active='movie-a', player='playing')
    await rig.run(before='movie-a')
    assert rig.calls[1][2]['item'] == {'file': 'smb://server/B.mkv'}
    assert rig.hass.states.get(SESSION).state == 'movie-b'


@pytest.mark.asyncio
async def test_old_queued_selection_cannot_open_current_movie(rig):
    rig.states(tag='movie-b', active='movie-a', player='playing')
    await rig.run(before='', after='movie-a')
    assert rig.calls == []


@pytest.mark.asyncio
async def test_unknown_tag_stops_previous_session(rig):
    rig.states(tag='unknown-movie', active='movie-a', player='playing')
    await rig.run(before='movie-a')
    assert 'kodi.call_method' not in service_names(rig)
    assert rig.hass.states.get(PLAYER).state == 'idle'


@pytest.mark.asyncio
@pytest.mark.parametrize('state', ['off', 'unknown', 'unavailable'])
async def test_no_open_when_kodi_unavailable(rig, state):
    rig.states(player=state)
    await rig.run()
    assert rig.calls == []
    assert rig.hass.states.get(SESSION).state == ''


@pytest.mark.asyncio
async def test_failed_open_keeps_cleanup_record(rig):
    rig.control.fail_open = True
    with pytest.raises(HomeAssistantError):
        await rig.run()
    assert rig.hass.states.get(SESSION).state == 'movie-a'


@pytest.mark.asyncio
async def test_failed_stop_retains_session_for_reconnect(rig):
    rig.states(active='movie-a', player='playing')
    rig.control.fail_stop = True
    with pytest.raises(HomeAssistantError):
        await rig.run('stop')
    assert rig.hass.states.get(SESSION).state == 'movie-a'
    rig.control.fail_stop = False
    await rig.run('kodi_reconnected')
    assert rig.hass.states.get(SESSION).state == ''


@pytest.mark.asyncio
async def test_silent_kodi_stop_failure_keeps_cleanup_record(rig):
    rig.states(active='movie-a', player='playing')
    rig.control.silent_stop_failure = True
    await rig.run('stop')
    assert rig.hass.states.get(SESSION).state == 'movie-a'
    assert rig.hass.states.get(PLAYER).state == 'playing'


@pytest.mark.asyncio
async def test_stop_while_kodi_unavailable_retries_on_reconnect(rig):
    rig.states(tag='', active='movie-a', player='unavailable')
    await rig.run('selection', before='movie-a')
    assert rig.calls == []
    assert rig.hass.states.get(SESSION).state == 'movie-a'
    rig.hass.states.async_set(PLAYER, 'playing')
    await rig.run('kodi_reconnected')
    assert rig.hass.states.get(SESSION).state == ''


@pytest.mark.asyncio
async def test_stop_after_natural_end_clears_helper(rig):
    rig.states(tag='', active='movie-a', player='idle')
    await rig.run('selection', before='movie-a')
    assert service_names(rig) == ['input_text.set_value']
    assert rig.hass.states.get(SESSION).state == ''


@pytest.mark.asyncio
async def test_kodi_open_error_stops_previous_movie(rig):
    rig.states(tag='movie-b', active='movie-b', player='playing')
    await rig.run('open_error')
    assert rig.hass.states.get(SESSION).state == ''
    assert rig.hass.states.get(PLAYER).state == 'idle'


@pytest.mark.asyncio
async def test_delayed_kodi_error_for_a_does_not_stop_b(rig):
    rig.states(tag='movie-b', active='movie-b', player='playing')
    await rig.run('open_error', failed_item={'movieid': 123})
    assert rig.calls == []
    assert rig.hass.states.get(SESSION).state == 'movie-b'


@pytest.mark.asyncio
async def test_removal_waits_behind_in_flight_open_then_stops(rig):
    rig.control.open_gate = asyncio.Event()
    insert = asyncio.create_task(rig.run())
    for _ in range(30):
        if any(c[0] == 'kodi' for c in rig.calls): break
        await asyncio.sleep(0)
    assert rig.calls[1][1] == 'call_method'
    rig.hass.states.async_set(TAG, '')
    remove = asyncio.create_task(rig.run(before='movie-a'))
    await asyncio.sleep(0)
    rig.control.open_gate.set()
    await asyncio.gather(insert, remove)
    assert service_names(rig) == ['input_text.set_value', 'kodi.call_method',
                                  'media_player.media_stop', 'input_text.set_value']
    assert rig.hass.states.get(PLAYER).state == 'idle'


@pytest.mark.asyncio
async def test_triggers_use_only_selected_reader_and_press_edges(rig):
    triggers = rig.config['triggers']
    for kind in ['play', 'pause', 'stop']:
        t = next(t for t in triggers if t['id'] == kind)
        assert t['from'] == 'off' and t['to'] == 'on'
        assert t['entity_id'] == [INPUTS[f'{kind}_button']]
    offline = next(t for t in triggers if t['id'] == 'offline')
    assert offline['for'].total_seconds() == 3


@pytest.mark.asyncio
async def test_actual_state_and_event_triggers_are_scoped(rig):
    fired = []
    async def action(variables, context=None):
        fired.append(variables['trigger']['id'])
    rig.hass.states.async_set(INPUTS['play_button'], 'off')
    rig.hass.states.async_set('binary_sensor.other_play_button', 'off')
    await rig.hass.async_block_till_done()
    remove = await async_initialize_triggers(rig.hass, rig.config['triggers'], action,
                                             'automation', 'Test Movie Time', lambda *args, **kw: None)
    try:
        rig.hass.states.async_set('sensor.other_selected_tag', 'movie-b')
        rig.hass.states.async_set('binary_sensor.other_play_button', 'on')
        rig.hass.bus.async_fire('kodi_call_method_result', {
            'entity_id': 'media_player.other_kodi', 'result_ok': False,
            'input': {'method': 'Player.Open', 'params': {}}})
        await rig.hass.async_block_till_done()
        assert fired == []
        rig.hass.states.async_set(TAG, 'movie-b')
        rig.hass.states.async_set(INPUTS['play_button'], 'on')
        rig.hass.bus.async_fire('kodi_call_method_result', {
            'entity_id': PLAYER, 'result_ok': False,
            'input': {'method': 'Player.Open', 'params': {'item': {'movieid': 123}}}})
        await rig.hass.async_block_till_done()
        assert sorted(fired) == ['open_error', 'play', 'selection']
        rig.hass.states.async_set(INPUTS['play_button'], 'off')
        await rig.hass.async_block_till_done()
        assert len(fired) == 3
    finally:
        remove()
