import type { ComponentType } from "react";
import type { KnownScreen, ScreenOut } from "../../../../api/appTypes";
import { RoleplayScreen } from "../RoleplayScreen";
import { LearnScreen } from "./LearnScreen";
import { PhrasesReviewScreen } from "./PhrasesReviewScreen";
import { PlanScreen } from "./PlanScreen";
import { ScenarioScreen } from "./ScenarioScreen";
import { SetupScreen } from "./SetupScreen";
import type { ScreenProps, ScreenRegistry } from "./types";
import { UnsupportedScreen } from "./UnsupportedScreen";
import { WrapScreen } from "./WrapScreen";

/** `{screenType: Component}`. */
export const SCREEN_REGISTRY: ScreenRegistry = {
  setup_question: SetupScreen,
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
