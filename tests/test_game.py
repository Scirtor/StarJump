import json
import math

import pygame
import pytest

from starjump.app import Game
from starjump.input import Input
from starjump.storage import Storage
from starjump.world import Commands, SpatialGrid, STEP, World


def settle(world, frames=90):
    for _ in range(frames):
        world.step(Commands())


def test_spatial_lookup_negative_coordinates_and_cell_edges():
    grid = SpatialGrid([[-192, -96, 96, 96], [-96, -96, 96, 96], [0, 0, 96, 96]])
    assert grid.query(pygame.FRect(-150, -50, 20, 20)) == (pygame.Rect(-192, -96, 96, 96),)
    assert grid.query(pygame.Rect(-96, -96, 96, 96)) == (pygame.Rect(-96, -96, 96, 96),)
    assert len(grid.query(pygame.FRect(-1, -1, 2, 2))) == 2


def test_grid_candidates_include_every_actual_overlap():
    world = World()
    for x in range(-210, 4200, 137):
        for y in range(-2200, 900, 179):
            r = pygame.FRect(x + .3, y + .6, 48, 60)
            broad = world.solids.query(r)
            assert all(b in broad for b in world.solids.rects if r.colliderect(b))


def test_player_lands_and_double_jump_does_not_allow_third_jump():
    world = World()
    settle(world)
    assert world.grounded and world.player.bottom == 624
    world.step(Commands(jump=True))
    assert world.jumps == 1 and world.vy < 0
    for _ in range(12):
        world.step(Commands())
    world.step(Commands(jump=True))
    assert world.jumps == 2
    for _ in range(4):
        world.step(Commands())
    before = world.vy
    world.step(Commands(jump=True))
    assert world.jumps == 2 and world.vy >= before


def test_against_wall_and_ceiling_player_never_enters_solid_tiles():
    world = World()
    settle(world)
    for i in range(220):
        world.step(Commands(left=True, jump=i in (0, 16, 100, 116)))
        assert not any(world.player.colliderect(b) for b in world.solids.rects)


def test_checkpoint_restores_player_and_keeps_collected_coins():
    world = World()
    world.checkpoint = 1
    world.coins.pop(0)
    world.collected = 1
    world.respawn()
    assert world.player.midbottom == (3216, -816)
    assert world.collected == 1 and 0 not in world.coins
    assert world.deaths == 1


def test_hazard_respawns_once():
    world = World()
    hazard = world.hazards.rects[0]
    world.player.topleft = hazard.topleft
    world.step(Commands())
    assert world.deaths == 1
    assert world.player.topleft == tuple(world.start)


def test_progress_is_clamped_and_goal_finishes_run():
    world = World()
    world.max_height = -9000
    assert world.progress == 1
    world.max_height = 9000
    assert world.progress == 0
    world.player.center = world.goal.center
    world.step(Commands())
    assert world.won
    old = world.elapsed
    world.step(Commands(right=True))
    assert world.elapsed == old


def test_multitouch_holding_move_and_tapping_jump():
    inp = Input()
    inp.layout(1280, 720)
    inp.finger(1, inp.buttons['right'].center)
    inp.finger(2, inp.buttons['jump'].center)
    c = inp.commands()
    assert c.right and c.jump
    assert not inp.commands().jump
    inp.finger(2, (0, 0), False)
    assert inp.commands().right
    inp.finger(2, inp.buttons['jump'].center)
    assert inp.commands().jump
    inp.clear()
    assert inp.commands() == Commands()


def test_dragging_finger_off_button_releases_it():
    inp = Input()
    inp.layout(720, 1440)
    inp.finger(1, inp.buttons['left'].center)
    assert inp.commands().left
    inp.finger(1, (360, 360))
    assert not inp.commands().left


@pytest.fixture
def game(tmp_path):
    return Game(storage=Storage(tmp_path / 'save.json'), touch=True)


def test_physics_identical_at_30_60_and_120_render_fps(tmp_path):
    states = []
    for fps in (30, 60, 120):
        game = Game(storage=Storage(tmp_path / f'{fps}.json'))
        game.start()
        game.input.keys.add(pygame.K_d)
        for _ in range(fps):
            game.update(1 / fps)
        states.append((tuple(game.world.player), game.world.elapsed))
    assert states[0] == states[1] == states[2]


def test_pause_and_focus_loss_clear_keys_fingers_and_time(game):
    game.start()
    game.input.keys.add(pygame.K_d)
    game.input.finger(5, game.input.buttons['jump'].center)
    game.event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    assert game.state == 'paused'
    old = tuple(game.world.player), game.world.elapsed
    game.update(120)
    assert (tuple(game.world.player), game.world.elapsed) == old
    assert not game.input.keys and not game.input.fingers
    game.resume()
    game.update(STEP)
    assert game.world.elapsed == STEP


def test_emulated_touch_mouse_event_does_not_double_jump(game):
    game.start()
    p = game.input.buttons['jump'].center
    game.event(pygame.event.Event(pygame.FINGERDOWN, x=p[0]/1280, y=p[1]/720, finger_id=1))
    game.update(STEP)
    game.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=p, button=1, touch=True))
    game.update(STEP)
    assert game.world.jumps == 1


def test_saved_progress_can_resume_and_win_clears_run(tmp_path):
    path = tmp_path / 'save.json'
    store = Storage(path)
    world = World()
    world.checkpoint = 2
    world.elapsed = 98.5
    world.coins.pop(1)
    world.collected = 1
    assert store.save_world(world)
    restored = World()
    assert Storage(path).restore_world(restored)
    assert restored.checkpoint == 2 and restored.elapsed == 98.5
    assert 1 not in restored.coins and restored.collected == 1
    assert store.finish(restored)
    assert 'run' not in Storage(path).data
    assert Storage(path).data['best_seconds'] == 98.5


@pytest.mark.parametrize('value', ['broken json', '[]', '{"run":{"checkpoint":999}}'])
def test_corrupt_or_invalid_save_is_safe(tmp_path, value):
    path = tmp_path / 'save.json'
    path.write_text(value)
    store = Storage(path)
    assert not store.restore_world(World())


def test_portrait_and_landscape_controls_remain_on_screen(game):
    for size in ((390, 844), (844, 390), (1280, 720)):
        game.resize(size)
        view = pygame.Rect((0, 0), game.view_size)
        assert all(view.contains(r) for r in game.input.buttons.values())
        assert game.surface.get_width() * game.surface.get_height() <= 1280 * 1440


def test_no_image_loads_after_warmup_and_only_visible_blocks_drawn(game):
    game.start()
    game.render(False)
    loads = game.assets.loads
    for _ in range(90):
        game.update(STEP)
        game.render(False)
    assert game.assets.loads == loads
    assert game.drawn_blocks < len(game.world.solids.rects) // 2
    assert game.world.collision_candidates < 20


def test_entire_level_can_be_completed_using_only_movement_and_jump_inputs():
    from pathlib import Path
    route = json.loads(Path(__file__).with_name('completion-route.json').read_text())
    world = World()
    for move, jump in route:
        world.step(Commands(left=move < 0, right=move > 0, jump=jump))
        assert not any(world.player.colliderect(b) for b in world.solids.query(world.player))
    assert world.won and world.deaths == 0


@pytest.mark.parametrize('value', [
    '{"run":{"elapsed":NaN}}', '{"run":{"max_height":Infinity}}',
    '{"run":{"collected_ids":"not a list"}}', '{"best_seconds":NaN}'
])
def test_nonfinite_and_malformed_save_values_do_not_crash(tmp_path, value):
    path = tmp_path / 'save.json'
    path.write_text(value)
    store = Storage(path)
    assert not store.restore_world(World())
    assert 'best_seconds' not in store.data


def test_continue_menu_buttons_stay_clear_of_footer(game):
    game.storage.data = {'run': {'checkpoint': 0}, 'best_seconds': 58}
    for size in ((1920, 900), (844, 390), (2560, 960), (390, 844)):
        game.resize(size)
        game.state = 'menu'
        game.render(False)
        assert len(game.ui_buttons) == 3
        assert all(r.top >= 0 and r.bottom < game.view_size[1] - 46 for r in game.ui_buttons.values())


def test_help_back_button_fits_short_landscape_screen(game):
    game.resize((2560, 960))
    game.state = 'help'
    game.render(False)
    assert game.ui_buttons['back'].bottom <= game.view_size[1] - 20
