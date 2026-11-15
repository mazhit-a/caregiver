import type { ComponentType } from "react";
import type { KnownScreen, ScreenOut } from "../../../../api/appTypes";
import { RoleplayScreen } from "../RoleplayScreen";
import { BuilderScreen } from "./BuilderScreen";
import { ContentScreen } from "./ContentScreen";
import { IntroScreen } from "./IntroScreen";
import { LearnScreen } from "./LearnScreen";
import { PhrasesReviewScreen } from "./PhrasesReviewScreen";
import { PlanScreen } from "./PlanScreen";
import { QuizScreen } from "./QuizScreen";
import { ResetScreen } from "./ResetScreen";
import { ScenarioScreen } from "./ScenarioScreen";
import { SetupScreen } from "./SetupScreen";
import type { ScreenProps, ScreenRegistry } from "./types";
import { UnsupportedScreen } from "./UnsupportedScreen";
import { WrapScreen } from "./WrapScreen";

/** `{screenType: Component}`. */
export const SCREEN_REGISTRY: ScreenRegistry = {
  // The lesson-1 (24 screens) types, then the older lessons' `setup_question` and `learn`.
  intro: IntroScreen,
  setup: SetupScreen,
  setup_question: SetupScreen,
  content: ContentScreen,
  quiz: QuizScreen,
  builder: BuilderScreen,
  reset: ResetScreen,
  scenario: ScenarioScreen,
  learn: LearnScreen,
  phrases_review: PhrasesReviewScreen,
  roleplay: RoleplayScreen,
  plan: PlanScreen,
  wrap: WrapScreen,
};

type AnyProps = Omit<ScreenProps<KnownScreen>, "screen">;

export function ScreenView({ screen, ...rest }: AnyProps & { screen: ScreenOut }) {
  if (screen.type === "unknown") return <UnsupportedScreen />;
  const Component = SCREEN_REGISTRY[screen.type] as ComponentType<ScreenProps<KnownScreen>>;
  return <Component screen={screen} {...rest} />;
}
