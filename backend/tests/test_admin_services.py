from app.db import Service, SessionLocal


def service_payload(category_id):
    return {
        'name': 'Admin Test Resource',
        'description': 'A test resource managed through the admin API.',
        'category_id': category_id,
        'location': 'Campus test office',
        'hours': 'Mon-Fri 9-5',
        'contact': 'Use the official page',
        'source_url': 'https://www.uta.edu/',
        'tags': ['admin-test'],
        'next_steps': ['Review the official page.', 'Contact the service.'],
        'active': True,
        'verified': False,
    }


def test_admin_can_create_update_archive_and_restore_service(client, admin, student):
    category_id = client.get('/api/categories').json()[0]['id']
    payload = service_payload(category_id)

    created = client.post('/api/v1/admin/services', json=payload, headers=admin)
    assert created.status_code == 201
    service_id = created.json()['id']
    assert any(item['id'] == service_id for item in client.get('/api/v1/admin/services', headers=admin).json())

    payload['description'] = 'Updated information managed through the versioned admin API.'
    updated = client.put(f'/api/v1/admin/services/{service_id}', json=payload, headers=admin)
    assert updated.status_code == 200
    assert updated.json()['description'] == payload['description']

    archived = client.delete(f'/api/v1/admin/services/{service_id}', headers=admin)
    assert archived.status_code == 200
    assert archived.json()['active'] is False
    assert client.get(f'/api/services/{service_id}', headers=student).status_code == 404
    assert all(item['id'] != service_id for item in client.get('/api/services').json()['items'])

    restored = client.patch(f'/api/v1/admin/services/{service_id}', json={'active': True}, headers=admin)
    assert restored.status_code == 200
    assert restored.json()['active'] is True
    assert client.get(f'/api/services/{service_id}', headers=student).status_code == 200


def test_admin_service_routes_reject_students_and_invalid_records(client, student, admin):
    category_id = client.get('/api/categories').json()[0]['id']
    payload = service_payload(category_id)

    assert client.post('/api/v1/admin/services', json=payload, headers=student).status_code == 403
    assert client.post('/api/v1/admin/services', json=payload, headers=admin).status_code == 201
    assert client.post(
        '/api/v1/admin/services',
        json={**payload, 'category_id': 999999},
        headers=admin,
    ).status_code == 422
    assert client.put(
        '/api/v1/admin/services/999999',
        json=payload,
        headers=admin,
    ).status_code == 404
    assert client.delete('/api/v1/admin/services/999999', headers=admin).status_code == 404


def test_archived_service_remains_in_admin_directory(client, admin):
    category_id = client.get('/api/categories').json()[0]['id']
    created = client.post(
        '/api/v1/admin/services',
        json=service_payload(category_id),
        headers=admin,
    )
    service_id = created.json()['id']

    assert client.delete(f'/api/v1/admin/services/{service_id}', headers=admin).status_code == 200
    assert any(
        item['id'] == service_id and item['active'] is False
        for item in client.get('/api/v1/admin/services', headers=admin).json()
    )
    with SessionLocal() as db:
        assert db.get(Service, service_id) is not None