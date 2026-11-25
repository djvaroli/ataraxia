/** Changes to a lesson's state (saved, rating, finished, flag), shown at once and confirmed by the server. */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { keys } from '../../app/queries';
import { useApi } from '../../app/services';
import type { Lesson, LessonState, Rating } from '../../lib/api';

type Change =
  | { kind: 'saved'; value: boolean }
  | { kind: 'rating'; value: Rating }
  | { kind: 'finished'; value: boolean }
  | { kind: 'flag'; note: string };

function apply(state: LessonState, change: Change): LessonState {
  const now = new Date().toISOString();
  switch (change.kind) {
    case 'saved':
      return {
        ...state,
        saved: change.value,
        saved_at: change.value ? now : null,
      };
    case 'rating':
      return { ...state, rating: change.value };
    case 'finished':
      return { ...state, finished_at: change.value ? now : null };
    case 'flag':
      return { ...state, flagged: true };
  }
}

export function useLessonState(lessonId: string) {
  const api = useApi();
  const client = useQueryClient();
  const key = keys.lesson(lessonId);

  const setState = (state: LessonState) =>
    client.setQueryData<Lesson>(key, (lesson) =>
      lesson ? { ...lesson, state } : lesson,
    );

  return useMutation({
    // One change at a time, so responses and rollbacks cannot arrive out of order.
    scope: { id: `lesson-state-${lessonId}` },
    mutationFn: (change: Change): Promise<LessonState> => {
      switch (change.kind) {
        case 'saved':
          return api.setSaved(lessonId, change.value);
        case 'rating':
          return api.setRating(lessonId, change.value);
        case 'finished':
          return api.setFinished(lessonId, change.value);
        case 'flag':
          return api.flagLesson(lessonId, change.note);
      }
    },
    onMutate: async (change) => {
      await client.cancelQueries({ queryKey: key });
      const previous = client.getQueryData<Lesson>(key);
      if (previous) setState(apply(previous.state, change));
      return { previous };
    },
    onError: (_error, _change, context) => {
      if (context?.previous) client.setQueryData(key, context.previous);
    },
    onSuccess: (state) => {
      setState(state);
    },
    onSettled: () => {
      void client.invalidateQueries({ queryKey: key });
      void client.invalidateQueries({ queryKey: keys.today });
      void client.invalidateQueries({ queryKey: keys.lessonsAll });
      void client.invalidateQueries({ queryKey: keys.progress });
    },
  });
}
