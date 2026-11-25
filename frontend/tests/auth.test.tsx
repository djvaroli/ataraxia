import { screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';
import { createFakeAuth } from '../src/fake/auth';
import { FakeServer } from '../src/fake/server';
import { NOW, renderApp } from './render';

describe('Sign-in', () => {
  test('signs in and sends the ID token with every request', async () => {
    const auth = createFakeAuth();
    const { server, user } = renderApp({ auth });

    await user.type(await screen.findByLabelText('Email'), 'owner@example.com');
    await user.type(screen.getByLabelText('Password'), 'correct horse');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByText('Another lesson')).toBeVisible();
    const application = server.requests.filter(
      (request) => !request.path.endsWith('/client-config'),
    );
    expect(application.length).toBeGreaterThan(0);
    application.forEach((request) =>
      expect(request.authorization).toBe('Bearer fake-id-token'),
    );
    const [config] = server.requestsTo('GET', /client-config$/);
    expect(config.authorization).toBeNull();
  });

  test('explains a wrong password', async () => {
    const { user } = renderApp({ auth: createFakeAuth() });
    await user.type(await screen.findByLabelText('Email'), 'owner@example.com');
    await user.type(screen.getByLabelText('Password'), 'wrong');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That email and password don’t match.',
    );
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled();
  });

  test('explains rate limiting', async () => {
    const { user } = renderApp({
      auth: createFakeAuth({ failWith: 'auth/too-many-requests' }),
    });
    await user.type(await screen.findByLabelText('Email'), 'owner@example.com');
    await user.type(screen.getByLabelText('Password'), 'x');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      /Too many attempts/,
    );
  });

  test('returns to sign-in when the API says the session ended', async () => {
    const auth = createFakeAuth({ signedIn: true });
    const { server } = renderApp({ auth, path: '/library' });
    server.failNext({
      path: /\/today$|\/me$|\/lessons$/,
      status: 401,
      code: 'unauthenticated',
      message: 'Sign in again.',
      times: 5,
    });
    expect(
      await screen.findByRole('button', { name: 'Sign in' }),
    ).toBeVisible();
    expect(screen.getByRole('status')).toHaveTextContent('Your session ended');
    expect(auth.signedIn()).toBe(false);
  });

  test('tells another account it is not the owner', async () => {
    const auth = createFakeAuth({ signedIn: true });
    const { server, user } = renderApp({ auth });
    server.failNext({
      path: /./,
      status: 403,
      code: 'forbidden',
      message: 'Not the owner.',
      times: 10,
    });
    expect(
      await screen.findByRole('heading', {
        name: 'This account isn’t the owner.',
      }),
    ).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(
      await screen.findByRole('button', { name: 'Sign in' }),
    ).toBeVisible();
  });

  test('offers a retry when the server cannot be reached', async () => {
    const server = new FakeServer({ now: () => NOW });
    server.failNext({
      path: /client-config$/,
      status: 503,
      code: 'unavailable',
      message: 'Ataraxia is starting up.',
    });
    const { user } = renderApp({ server });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ataraxia is starting up.',
    );
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('Another lesson')).toBeVisible();
  });
});
