"""Unit tests for the SimulationResponse schema."""
from src.server.enums import ClientErrorMessage, ResponseStatus
from src.server.schemas import SimulationResponse


def test_success_to_dict_carries_payload_and_status():
    # Arrange
    response = SimulationResponse.success(simulation=[[1.0]], shape=[1, 1])

    # Act
    payload = response.to_dict()

    # Assert
    assert payload == {
        "simulation": [[1.0]],
        "shape": [1, 1],
        "status": "success",
        "error": None,
    }
    assert response.is_error is False


def test_failure_returns_generic_message_and_no_payload():
    # Arrange
    response = SimulationResponse.failure(ClientErrorMessage.SIMULATION_FAILED)

    # Act
    payload = response.to_dict()

    # Assert: client-safe message, no simulation data, error status.
    assert payload == {
        "simulation": None,
        "shape": None,
        "status": "error",
        "error": "Simulation failed",
    }
    assert response.is_error is True


def test_success_and_failure_share_the_same_keys():
    # Arrange
    success = SimulationResponse.success(simulation=[[0.0]], shape=[1, 1]).to_dict()
    failure = SimulationResponse.failure(ClientErrorMessage.SIMULATION_FAILED).to_dict()

    # Act
    success_keys = set(success)
    failure_keys = set(failure)

    # Assert: one stable schema regardless of outcome.
    assert success_keys == failure_keys


def test_status_is_an_enum_not_a_magic_string():
    # Arrange / Act
    response = SimulationResponse.success(simulation=[[1.0]], shape=[1, 1])

    # Assert
    assert response.status is ResponseStatus.SUCCESS
